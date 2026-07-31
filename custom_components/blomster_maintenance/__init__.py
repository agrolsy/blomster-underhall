from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_BASELINE_LITERS,
    ATTR_ITEM_ID,
    ATTR_METER_ENTITY,
    ATTR_NAME,
    ATTR_NOTE,
    CONF_WATER_INSTALLATION_DATE,
    CONF_WATER_SOURCE_ENTITY,
    DOMAIN,
    EVENT_MAINTENANCE_UPDATED,
    EVENT_WATER_UPDATED,
    SERVICE_RECORD_MAINTENANCE,
    SERVICE_SET_WATER_BASELINE,
)
from .storage import MaintenanceStore
from .water import async_start_water_tracking

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

BASELINE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_BASELINE_LITERS): vol.All(vol.Coerce(float), vol.Range(min=0))}
)
RECORD_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ITEM_ID): cv.string,
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_METER_ENTITY): cv.entity_id,
        vol.Optional(ATTR_NOTE): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = MaintenanceStore(hass)
    await store.async_load()
    await store.async_configure_water(
        source_entity=entry.data[CONF_WATER_SOURCE_ENTITY],
        installation_date=entry.data[CONF_WATER_INSTALLATION_DATE].isoformat()
        if hasattr(entry.data[CONF_WATER_INSTALLATION_DATE], "isoformat")
        else str(entry.data[CONF_WATER_INSTALLATION_DATE]),
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = store

    remove_listener = await async_start_water_tracking(hass, store)
    if remove_listener:
        entry.async_on_unload(remove_listener)

    async def set_water_baseline(call: ServiceCall) -> None:
        state = hass.states.get(store.water.source_entity) if store.water.source_entity else None
        current_value = None
        if state and state.state not in {"unknown", "unavailable"}:
            try:
                current_value = float(state.state)
            except (TypeError, ValueError) as err:
                raise HomeAssistantError("Vattenkällans värde är inte numeriskt") from err
        await store.async_set_baseline(call.data[ATTR_BASELINE_LITERS], current_value)
        hass.bus.async_fire(EVENT_WATER_UPDATED)

    async def record_maintenance(call: ServiceCall) -> None:
        meter_entity = call.data.get(ATTR_METER_ENTITY)
        meter_value = None
        meter_unit = None
        if meter_entity:
            state = hass.states.get(meter_entity)
            if state is None or state.state in {"unknown", "unavailable"}:
                raise HomeAssistantError("Den valda mätarentiteten saknar ett tillgängligt värde")
            try:
                meter_value = float(state.state)
            except (TypeError, ValueError) as err:
                raise HomeAssistantError("Den valda mätarentitetens värde är inte numeriskt") from err
            meter_unit = state.attributes.get("unit_of_measurement")

        item = await store.async_record(
            item_id=call.data[ATTR_ITEM_ID],
            name=call.data[ATTR_NAME],
            meter_value=meter_value,
            meter_entity=meter_entity,
            meter_unit=meter_unit,
            note=call.data.get(ATTR_NOTE),
        )
        hass.bus.async_fire(EVENT_MAINTENANCE_UPDATED, {"item_id": item.item_id})

    hass.services.async_register(
        DOMAIN, SERVICE_SET_WATER_BASELINE, set_water_baseline, schema=BASELINE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RECORD_MAINTENANCE, record_maintenance, schema=RECORD_SCHEMA
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_WATER_BASELINE)
            hass.services.async_remove(DOMAIN, SERVICE_RECORD_MAINTENANCE)
    return unloaded
