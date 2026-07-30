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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    store: MaintenanceStore = hass.data[DOMAIN][entry.entry_id]
    water = WaterTotalSensor(store)
    blade = BladeRemainingSensor(hass, entry)
    entities: dict[str, MaintenanceSensor] = {}
    async_add_entities([water, blade])

    @callback
    def sync_water(_event=None) -> None:
        water.async_write_ha_state()

    @callback
    def sync_items(_event=None) -> None:
        new_entities = []
        for item_id in store.items:
            if item_id not in entities:
                entity = MaintenanceSensor(store, item_id)
                entities[item_id] = entity
                new_entities.append(entity)
        if new_entities:
            async_add_entities(new_entities)
        for entity in entities.values():
            entity.async_write_ha_state()

    sync_items()
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

    def __init__(self, store: MaintenanceStore) -> None:
        self._store = store

    @property
    def native_value(self) -> float:
        return round(self._store.water.accumulated_liters, 3)

    @property
    def extra_state_attributes(self):
        water = self._store.water
        return {
            "source_entity": water.source_entity,
            "installation_date": water.installation_date,
            "last_source_value": water.last_source_value,
            "last_updated": water.last_updated,
            "method": "manual_baseline_plus_daily_delta",
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

    def __init__(self, store: MaintenanceStore, item_id: str) -> None:
        self._store = store
        self._item_id = item_id
        self._attr_unique_id = f"{DOMAIN}_{item_id}"

    @property
    def name(self) -> str:
        return self._store.items[self._item_id].name

    @property
    def native_value(self):
        events = self._store.items[self._item_id].events
        return events[-1].performed_at if events else "Ej registrerat"

    @property
    def extra_state_attributes(self):
        item = self._store.items[self._item_id]
        return {
            "item_id": item.item_id,
            "history": [
                {
                    "performed_at": event.performed_at,
                    "meter_value": event.meter_value,
                    "note": event.note,
                }
                for event in item.events
            ],
        }
