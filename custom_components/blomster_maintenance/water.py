from __future__ import annotations

import logging

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import EVENT_WATER_UPDATED
from .storage import MaintenanceStore

_LOGGER = logging.getLogger(__name__)


async def async_start_water_tracking(hass: HomeAssistant, store: MaintenanceStore):
    source_entity = store.water.source_entity
    if not source_entity:
        return None

    async def async_process(raw_value: str) -> None:
        if raw_value in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            _LOGGER.warning("Kan inte tolka vattenvärdet %s från %s", raw_value, source_entity)
            return
        if value < 0:
            return
        if await store.async_add_source_value(value):
            hass.bus.async_fire(EVENT_WATER_UPDATED)

    @callback
    def state_changed(event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is not None:
            hass.async_create_task(async_process(new_state.state))

    current = hass.states.get(source_entity)
    if current is not None:
        await async_process(current.state)

    return async_track_state_change_event(hass, [source_entity], state_changed)
