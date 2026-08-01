from __future__ import annotations

from datetime import datetime, timedelta

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
    SERVICEBOOK_SENSOR_UNIQUE_ID,
    WATER_SENSOR_UNIQUE_ID,
)
from .storage import MaintenanceItem, MaintenanceStore

_PREDEFINED_ITEMS = {"luba_blades": "Luba-knivar", "water_filter": "Vattenfilter"}
_INACTIVE_WARNING_STATES = {"", "0", "false", "none", "off", "ok", "unknown", "unavailable"}


def _numeric_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None or state.state in {"unknown", "unavailable"}:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


def _state_hours(hass: HomeAssistant, entity_id: str) -> float | None:
    value = _numeric_state(hass, entity_id)
    if value is None:
        return None
    state = hass.states.get(entity_id)
    unit = state.attributes.get("unit_of_measurement") if state else None
    if unit in {"s", "sec", "seconds"}:
        return value / 3600
    if unit in {"min", "minutes"}:
        return value / 60
    return value


def _live_accumulated_liters(hass: HomeAssistant, store: MaintenanceStore) -> float:
    accumulated = store.water.accumulated_liters
    source_entity = store.water.source_entity
    previous = store.water.last_source_value
    current = _numeric_state(hass, source_entity)
    if current is None or previous is None:
        return accumulated
    pending_delta = current - previous if current >= previous else current
    return accumulated + max(0.0, pending_delta)


def _item_status(hass: HomeAssistant, item: MaintenanceItem) -> dict:
    if not item.interval_type or not item.interval_value:
        return {"status": "not_configured", "remaining": None, "next_due": None}
    if not item.events:
        return {"status": "never", "remaining": 0, "next_due": None}

    last = item.events[-1]
    remaining: float | None = None
    next_due: str | None = None
    if item.interval_type == "days":
        due = datetime.fromisoformat(last.performed_at) + timedelta(days=item.interval_value)
        remaining = (due - datetime.now().astimezone()).total_seconds() / 86400
        next_due = due.isoformat()
    else:
        current = _numeric_state(hass, item.meter_entity)
        if current is not None and last.meter_value is not None:
            remaining = item.interval_value - max(0.0, current - last.meter_value)

    if remaining is None:
        status = "unknown"
    elif remaining <= 0:
        status = "overdue"
    elif remaining <= max(1.0, item.interval_value * 0.1):
        status = "due_soon"
    else:
        status = "ok"
    return {"status": status, "remaining": round(remaining, 2) if remaining is not None else None, "next_due": next_due}


def _item_problem_signature(hass: HomeAssistant, item: MaintenanceItem) -> str | None:
    status = _item_status(hass, item)["status"]
    reasons = [status] if status in {"never", "due_soon", "overdue"} else []
    for entity_id in item.warning_entities:
        state = hass.states.get(entity_id)
        value = state.state.strip().casefold() if state else "unavailable"
        if value not in _INACTIVE_WARNING_STATES:
            reasons.append(f"{entity_id}={value}")
    return "|".join(reasons) or None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    store: MaintenanceStore = hass.data[DOMAIN][entry.entry_id]
    water = WaterTotalSensor(hass, store)
    blade = BladeRemainingSensor(hass, entry)
    water_since_filter = WaterSinceFilterSensor(hass, store)
    servicebook = ServiceBookSensor(hass, store)
    entities: dict[str, MaintenanceSensor] = {
        item_id: MaintenanceSensor(hass, store, item_id, name)
        for item_id, name in _PREDEFINED_ITEMS.items()
    }
    async_add_entities([water, blade, water_since_filter, servicebook, *entities.values()])

    @callback
    def sync_water(_event=None) -> None:
        water.async_write_ha_state()
        water_since_filter.async_write_ha_state()
        servicebook.async_write_ha_state()

    @callback
    def sync_items(_event=None) -> None:
        new_entities = []
        for item_id, item in store.items.items():
            if item_id not in entities:
                entity = MaintenanceSensor(hass, store, item_id, item.name)
                entities[item_id] = entity
                new_entities.append(entity)
        if new_entities:
            async_add_entities(new_entities)
        for entity in entities.values():
            entity.async_write_ha_state()
        water_since_filter.async_write_ha_state()
        servicebook.async_write_ha_state()

    entry.async_on_unload(hass.bus.async_listen(EVENT_WATER_UPDATED, sync_water))
    entry.async_on_unload(hass.bus.async_listen(EVENT_MAINTENANCE_UPDATED, sync_items))


class WaterTotalSensor(SensorEntity):
    _attr_name = "Ackumulerad vattenförbrukning"
    _attr_unique_id = WATER_SENSOR_UNIQUE_ID
    _attr_icon = "mdi:water"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, hass: HomeAssistant, store: MaintenanceStore) -> None:
        self.hass = hass
        self._store = store

    @property
    def native_value(self) -> float | None:
        if not self._store.water.baseline_established:
            return None
        return round(_live_accumulated_liters(self.hass, self._store), 3)

    @property
    def extra_state_attributes(self):
        return {
            "source_entity": self._store.water.source_entity,
            "installation_date": self._store.water.installation_date,
            "baseline_established": self._store.water.baseline_established,
            "imported_from_recorder": self._store.water.imported_from_recorder,
        }


class WaterSinceFilterSensor(SensorEntity):
    _attr_name = "Vatten sedan filterbyte"
    _attr_unique_id = f"{DOMAIN}_water_since_filter"
    _attr_icon = "mdi:water-sync"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, hass: HomeAssistant, store: MaintenanceStore) -> None:
        self.hass = hass
        self._store = store

    @property
    def native_value(self) -> float | None:
        item = self._store.items.get("water_filter")
        if not item or not item.events or item.events[-1].meter_value is None:
            return None
        return round(max(0.0, _live_accumulated_liters(self.hass, self._store) - item.events[-1].meter_value), 3)


class BladeRemainingSensor(SensorEntity):
    _attr_name = "Luba blad återstående tid"
    _attr_unique_id = BLADE_REMAINING_SENSOR_UNIQUE_ID
    _attr_icon = "mdi:content-cut"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._usage_entity = entry.options.get(CONF_BLADE_USAGE_ENTITY, entry.data[CONF_BLADE_USAGE_ENTITY])
        self._interval = float(entry.options.get(CONF_BLADE_INTERVAL_HOURS, entry.data[CONF_BLADE_INTERVAL_HOURS]))

    @property
    def native_value(self) -> float | None:
        used = _state_hours(self.hass, self._usage_entity)
        return None if used is None else round(max(0.0, self._interval - used), 2)


class ServiceBookSensor(SensorEntity):
    _attr_name = "Servicebok"
    _attr_unique_id = SERVICEBOOK_SENSOR_UNIQUE_ID
    _attr_icon = "mdi:book-wrench"

    def __init__(self, hass: HomeAssistant, store: MaintenanceStore) -> None:
        self.hass = hass
        self._store = store

    @property
    def native_value(self) -> int:
        return sum(
            1
            for item in self._store.items.values()
            if (signature := _item_problem_signature(self.hass, item))
            and signature != item.acknowledged_signature
        )

    @property
    def extra_state_attributes(self):
        year = datetime.now().year
        rows = []
        total_cost = 0.0
        for item in self._store.items.values():
            status = _item_status(self.hass, item)
            rows.append({"item_id": item.item_id, "name": item.name, **status})
            total_cost += sum(event.cost or 0 for event in item.events if datetime.fromisoformat(event.performed_at).year == year)
        return {
            "overdue": [row for row in rows if row["status"] == "overdue"],
            "upcoming": [row for row in rows if row["status"] == "due_soon"],
            "latest": sorted(
                [{"item_id": item.item_id, "name": item.name, "performed_at": item.events[-1].performed_at} for item in self._store.items.values() if item.events],
                key=lambda row: row["performed_at"], reverse=True,
            )[:10],
            "total_cost_year": round(total_cost, 2),
            "year": year,
        }


class MaintenanceSensor(SensorEntity):
    _attr_icon = "mdi:tools"

    def __init__(self, hass: HomeAssistant, store: MaintenanceStore, item_id: str, default_name: str) -> None:
        self.hass = hass
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
        if not item:
            return {"item_id": self._item_id, "registered": False, "history": []}
        status = _item_status(self.hass, item)
        return {
            "item_id": item.item_id,
            "registered": bool(item.events),
            "category": item.category,
            "location": item.location,
            "manufacturer": item.manufacturer,
            "model": item.model,
            "serial_number": item.serial_number,
            "installed_at": item.installed_at,
            "interval_type": item.interval_type,
            "interval_value": item.interval_value,
            "meter_entity": item.meter_entity,
            "manual_url": item.manual_url,
            "receipt_url": item.receipt_url,
            "image_url": item.image_url,
            "warning_entities": item.warning_entities,
            "problem": bool((signature := _item_problem_signature(self.hass, item)) and signature != item.acknowledged_signature),
            "acknowledged": bool(signature and signature == item.acknowledged_signature),
            **status,
            "total_cost": round(sum(event.cost or 0 for event in item.events), 2),
            "history": [
                {
                    "event_id": event.event_id,
                    "performed_at": event.performed_at,
                    "meter_value": event.meter_value,
                    "meter_entity": event.meter_entity,
                    "meter_unit": event.meter_unit,
                    "note": event.note,
                    "cost": event.cost,
                }
                for event in item.events
            ],
        }
