from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BLADE_DUE_BINARY_SENSOR_UNIQUE_ID,
    CONF_BLADE_INTERVAL_HOURS,
    CONF_BLADE_USAGE_ENTITY,
    CONF_BLADE_WARNING_ENTITY,
)
from .sensor import _state_hours

_INACTIVE_WARNING_STATES = {"", "0", "false", "none", "off", "ok", "unknown", "unavailable"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([BladeReplacementDueBinarySensor(hass, entry)])


class BladeReplacementDueBinarySensor(BinarySensorEntity):
    _attr_name = "Luba blad behöver bytas"
    _attr_unique_id = BLADE_DUE_BINARY_SENSOR_UNIQUE_ID
    _attr_icon = "mdi:content-cut"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._usage_entity = entry.data[CONF_BLADE_USAGE_ENTITY]
        self._warning_entity = entry.data[CONF_BLADE_WARNING_ENTITY]
        self._interval = float(entry.data[CONF_BLADE_INTERVAL_HOURS])

    @property
    def is_on(self) -> bool:
        used = _state_hours(self.hass, self._usage_entity)
        warning = self.hass.states.get(self._warning_entity)
        warning_active = bool(
            warning
            and warning.state.strip().casefold() not in _INACTIVE_WARNING_STATES
        )
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
