from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BLADE_DUE_BINARY_SENSOR_UNIQUE_ID,
    CONF_BLADE_INTERVAL_HOURS,
    CONF_BLADE_USAGE_ENTITY,
    CONF_BLADE_WARNING_ENTITY,
    DOMAIN,
    EVENT_MAINTENANCE_UPDATED,
)
from .reminders import async_start_reminders
from .sensor import _item_problem_signature, _state_hours
from .storage import MaintenanceStore

_INACTIVE_WARNING_STATES = {"", "0", "false", "none", "off", "ok", "unknown", "unavailable"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entities: dict[str, MaintenanceProblemBinarySensor] = {}
    async_add_entities([BladeReplacementDueBinarySensor(hass, entry)])
    store: MaintenanceStore = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [entities.setdefault(item_id, MaintenanceProblemBinarySensor(hass, store, item_id)) for item_id in store.items]
    )

    @callback
    def sync_items(event: Event | None = None) -> None:
        if event and event.event_type == "state_changed":
            watched = {
                entity_id
                for item in store.items.values()
                for entity_id in [item.meter_entity, *item.warning_entities]
                if entity_id
            }
            if event.data.get("entity_id") not in watched:
                return
        new_entities = []
        for item_id in store.items:
            if item_id not in entities:
                entities[item_id] = MaintenanceProblemBinarySensor(hass, store, item_id)
                new_entities.append(entities[item_id])
        if new_entities:
            async_add_entities(new_entities)
        for entity in entities.values():
            entity.async_write_ha_state()

    entry.async_on_unload(hass.bus.async_listen(EVENT_MAINTENANCE_UPDATED, sync_items))
    entry.async_on_unload(hass.bus.async_listen("state_changed", sync_items))
    remove_reminders = await async_start_reminders(hass, store)
    entry.async_on_unload(remove_reminders)


class BladeReplacementDueBinarySensor(BinarySensorEntity):
    _attr_name = "Luba blad behöver bytas"
    _attr_unique_id = BLADE_DUE_BINARY_SENSOR_UNIQUE_ID
    _attr_icon = "mdi:content-cut"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._usage_entity = entry.options.get(CONF_BLADE_USAGE_ENTITY, entry.data[CONF_BLADE_USAGE_ENTITY])
        self._warning_entity = entry.options.get(CONF_BLADE_WARNING_ENTITY, entry.data[CONF_BLADE_WARNING_ENTITY])
        self._interval = float(entry.options.get(CONF_BLADE_INTERVAL_HOURS, entry.data[CONF_BLADE_INTERVAL_HOURS]))

    @property
    def is_on(self) -> bool:
        used = _state_hours(self.hass, self._usage_entity)
        warning = self.hass.states.get(self._warning_entity)
        warning_active = bool(warning and warning.state.strip().casefold() not in _INACTIVE_WARNING_STATES)
        return warning_active or (used is not None and used >= self._interval)

    @property
    def extra_state_attributes(self):
        warning = self.hass.states.get(self._warning_entity)
        return {
            "usage_entity": self._usage_entity,
            "warning_entity": self._warning_entity,
            "warning_state": warning.state if warning else None,
            "used_hours": _state_hours(self.hass, self._usage_entity),
            "replacement_interval_hours": self._interval,
        }


class MaintenanceProblemBinarySensor(BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:tools"

    def __init__(self, hass: HomeAssistant, store: MaintenanceStore, item_id: str) -> None:
        self.hass = hass
        self._store = store
        self._item_id = item_id
        self._attr_unique_id = f"{DOMAIN}_{item_id}_problem"

    @property
    def name(self) -> str:
        return f"{self._store.items[self._item_id].name} problem"

    @property
    def is_on(self) -> bool:
        item = self._store.items[self._item_id]
        signature = _item_problem_signature(self.hass, item)
        return bool(signature and signature != item.acknowledged_signature)

    @property
    def extra_state_attributes(self):
        item = self._store.items[self._item_id]
        signature = _item_problem_signature(self.hass, item)
        return {"item_id": self._item_id, "signature": signature, "acknowledged": signature == item.acknowledged_signature}
