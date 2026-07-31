from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BLADE_REMAINING_SENSOR_UNIQUE_ID,
    CONF_BLADE_INTERVAL_HOURS,
    CONF_BLADE_USAGE_ENTITY,
    DOMAIN,
    EVENT_MAINTENANCE_UPDATED,
    EVENT_WATER_UPDATED,
    WATER_SENSOR_UNIQUE_ID,
)
from .storage import MaintenanceStore

_PREDEFINED_ITEMS = {
    "luba_blades": "Luba-knivar",
    "water_filter": "Vattenfilter",
}


def _state_hours(hass: HomeAssistant, entity_id: str) -> float | None:
    state = hass.states.get(entity_id)
    if state is None or state.state in {"unknown", "unavailable"}:
        return None
    try:
        value = float(state.state)
    except (TypeError, ValueError):
        return None
    unit = state.attributes.get("unit_of_measurement")
    if unit in {"s", "sec", "seconds"}:
        return value / 3600
    if unit in {"min", "minutes"}:
        return value / 60
    return value


def _live_accumulated_liters(hass: HomeAssistant, store: MaintenanceStore) -> float:
    """Return stored accumulated water plus any not-yet-processed live source delta."""
    accumulated = store.water.accumulated_liters
    source_entity = store.water.source_entity
    previous = store.water.last_source_value
    if not source_entity or previous is None:
        return accumulated

    state = hass.states.get(source_entity)
    if state is None or state.state in {"unknown", "unavailable"}:
        return accumulated
    try:
        current = float(state.state)
    except (TypeError, ValueError):
        return accumulated

    # The source is a daily counter. If it resets at midnight, today's current
    # value is the delta. Otherwise only add the increase since last processing.
    pending_delta = current - previous if current >= previous else current
    return accumulated + max(0.0, pending_delta)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    store: MaintenanceStore = hass.data[DOMAIN][entry.entry_id]
    water = WaterTotalSensor(hass, store)
    blade = BladeRemainingSensor(hass, entry)
    water_since_filter = WaterSinceFilterSensor(hass, store)
    entities: dict[str, MaintenanceSensor] = {
        item_id: MaintenanceSensor(store, item_id, name)
        for item_id, name in _PREDEFINED_ITEMS.items()
    }
    async_add_entities([water, blade, water_since_filter, *entities.values()])

    @callback
    def sync_water(_event=None) -> None:
        water.async_write_ha_state()
        water_since_filter.async_write_ha_state()

    @callback
    def sync_items(_event=None) -> None:
        new_entities = []
        for item_id, item in store.items.items():
            if item_id not in entities:
                entity = MaintenanceSensor(store, item_id, item.name)
                entities[item_id] = entity
                new_entities.append(entity)
        if new_entities:
            async_add_entities(new_entities)
        for entity in entities.values():
            entity.async_write_ha_state()
        water_since_filter.async_write_ha_state()

    entry.async_on_unload(hass.bus.async_listen(EVENT_WATER_UPDATED, sync_water))
    entry.async_on_unload(hass.bus.async_listen(EVENT_MAINTENANCE_UPDATED, sync_items))


class WaterTotalSensor(SensorEntity):
    _attr_name = "Ackumulerad vattenförbrukning"
    _attr_unique_id = WATER_SENSOR_UNIQUE_ID
    _attr_icon = "mdi:water"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 1

    def __init__(self, hass: HomeAssistant, store: MaintenanceStore) -> None:
        self.hass = hass
        self._store = store

    @property
    def native_value(self) -> float:
        return round(_live_accumulated_liters(self.hass, self._store), 3)

    @property
    def extra_state_attributes(self):
        water = self._store.water
        return {
            "source_entity": water.source_entity,
            "installation_date": water.installation_date,
            "last_source_value": water.last_source_value,
            "last_updated": water.last_updated,
            "method": "manual_baseline_plus_live_daily_delta",
        }


class WaterSinceFilterSensor(SensorEntity):
    _attr_name = "Vatten sedan filterbyte"
    _attr_unique_id = f"{DOMAIN}_water_since_filter"
    _attr_icon = "mdi:water-sync"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, hass: HomeAssistant, store: MaintenanceStore) -> None:
        self.hass = hass
        self._store = store

    @property
    def native_value(self) -> float | None:
        item = self._store.items.get("water_filter")
        if not item or not item.events:
            return None
        baseline = item.events[-1].meter_value
        if baseline is None:
            return None
        current_total = _live_accumulated_liters(self.hass, self._store)
        return round(max(0.0, current_total - baseline), 3)

    @property
    def extra_state_attributes(self):
        item = self._store.items.get("water_filter")
        last_event = item.events[-1] if item and item.events else None
        return {
            "last_filter_change": last_event.performed_at if last_event else None,
            "baseline_liters": last_event.meter_value if last_event else None,
            "current_total_liters": round(_live_accumulated_liters(self.hass, self._store), 3),
            "source_entity": self._store.water.source_entity,
            "status": "Aldrig registrerat" if last_event is None else "Registrerat",
        }


class BladeRemainingSensor(SensorEntity):
    _attr_name = "Luba blad återstående tid"
    _attr_unique_id = BLADE_REMAINING_SENSOR_UNIQUE_ID
    _attr_icon = "mdi:content-cut"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._usage_entity = entry.data[CONF_BLADE_USAGE_ENTITY]
        self._interval = float(entry.data[CONF_BLADE_INTERVAL_HOURS])

    @property
    def native_value(self) -> float | None:
        used = _state_hours(self.hass, self._usage_entity)
        return None if used is None else round(max(0.0, self._interval - used), 2)

    @property
    def extra_state_attributes(self):
        used = _state_hours(self.hass, self._usage_entity)
        return {
            "usage_entity": self._usage_entity,
            "used_hours": used,
            "replacement_interval_hours": self._interval,
        }


class MaintenanceSensor(SensorEntity):
    _attr_icon = "mdi:tools"

    def __init__(self, store: MaintenanceStore, item_id: str, default_name: str) -> None:
        self._store = store
        self._item_id = item_id
        self._default_name = default_name
        self._attr_unique_id = f"{DOMAIN}_{item_id}"

    @property
    def name(self) -> str:
        item = self._store.items.get(self._item_id)
        return item.name if item else self._default_name

    @property
    def native_value(self):
        item = self._store.items.get(self._item_id)
        return item.events[-1].performed_at if item and item.events else "Aldrig registrerat"

    @property
    def extra_state_attributes(self):
        item = self._store.items.get(self._item_id)
        events = item.events if item else []
        return {
            "item_id": self._item_id,
            "registered": bool(events),
            "history": [
                {
                    "performed_at": event.performed_at,
                    "meter_value": event.meter_value,
                    "meter_entity": event.meter_entity,
                    "meter_unit": event.meter_unit,
                    "note": event.note,
                }
                for event in events
            ],
        }
