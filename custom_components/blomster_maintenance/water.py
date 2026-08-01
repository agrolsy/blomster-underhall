from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states

from .calculations import MeterSample, accumulated_meter_total, history_is_complete
from .const import EVENT_WATER_UPDATED
from .storage import MaintenanceStore

_LOGGER = logging.getLogger(__name__)


async def async_import_water_history(hass: HomeAssistant, store: MaintenanceStore) -> bool:
    """Import a complete Recorder series, refusing partial history."""
    if store.water.baseline_established or not store.water.source_entity or not store.water.installation_date:
        return store.water.baseline_established
    installation = datetime.fromisoformat(store.water.installation_date).astimezone()
    now = datetime.now().astimezone()
    try:
        result = await get_instance(hass).async_add_executor_job(
            get_significant_states,
            hass,
            installation,
            now,
            [store.water.source_entity],
            None,
            True,
            False,
            False,
            True,
        )
    except Exception:  # Recorder may still be starting or unavailable
        _LOGGER.exception("Recorder-historiken kunde inte läsas")
        return False
    samples: list[MeterSample] = []
    for state in result.get(store.water.source_entity, []):
        try:
            samples.append(MeterSample(float(state.state), state.last_updated))
        except (TypeError, ValueError):
            continue
    if not history_is_complete(samples, installation, now):
        _LOGGER.warning("Recorder-historiken för %s är ofullständig; vattenbaslinje krävs", store.water.source_entity)
        return False
    await store.async_set_imported_total(accumulated_meter_total(samples), samples[-1].value)
    return True


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
