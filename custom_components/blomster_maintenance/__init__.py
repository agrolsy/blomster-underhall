from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_BASELINE_LITERS,
    ATTR_CATEGORY,
    ATTR_COST,
    ATTR_EVENT_ID,
    ATTR_IMAGE_URL,
    ATTR_INSTALLED_AT,
    ATTR_INTERVAL_TYPE,
    ATTR_INTERVAL_VALUE,
    ATTR_ITEM_ID,
    ATTR_LOCATION,
    ATTR_MANUAL_URL,
    ATTR_MANUFACTURER,
    ATTR_METER_ENTITY,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_NOTE,
    ATTR_RECEIPT_URL,
    ATTR_SERIAL_NUMBER,
    CONF_WATER_INSTALLATION_DATE,
    CONF_WATER_SOURCE_ENTITY,
    DOMAIN,
    EVENT_MAINTENANCE_UPDATED,
    EVENT_WATER_UPDATED,
    SERVICE_CONFIGURE_ITEM,
    SERVICE_DELETE_MAINTENANCE,
    SERVICE_RECORD_MAINTENANCE,
    SERVICE_SET_WATER_BASELINE,
)
from .frontend import async_setup_frontend
from .storage import MaintenanceStore
from .water import async_start_water_tracking

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
CARD_URL = "/blomster_maintenance/blomster-maintenance-card.js"
CARD_PATH = Path(__file__).parent / "static" / "blomster-maintenance-card.js"
CARD_REGISTERED = f"{DOMAIN}_card_registered"

BASELINE_SCHEMA = vol.Schema({vol.Required(ATTR_BASELINE_LITERS): vol.All(vol.Coerce(float), vol.Range(min=0))})
CONFIGURE_SCHEMA = vol.Schema({
    vol.Required(ATTR_ITEM_ID): cv.string,
    vol.Required(ATTR_NAME): cv.string,
    vol.Optional(ATTR_CATEGORY): cv.string,
    vol.Optional(ATTR_LOCATION): cv.string,
    vol.Optional(ATTR_MANUFACTURER): cv.string,
    vol.Optional(ATTR_MODEL): cv.string,
    vol.Optional(ATTR_SERIAL_NUMBER): cv.string,
    vol.Optional(ATTR_INSTALLED_AT): cv.string,
    vol.Optional(ATTR_INTERVAL_TYPE): vol.In(["days", "liters", "hours", "starts"]),
    vol.Optional(ATTR_INTERVAL_VALUE): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional(ATTR_METER_ENTITY): cv.entity_id,
    vol.Optional(ATTR_MANUAL_URL): cv.string,
    vol.Optional(ATTR_RECEIPT_URL): cv.string,
    vol.Optional(ATTR_IMAGE_URL): cv.string,
})
RECORD_SCHEMA = vol.Schema({
    vol.Required(ATTR_ITEM_ID): cv.string,
    vol.Required(ATTR_NAME): cv.string,
    vol.Optional(ATTR_METER_ENTITY): cv.entity_id,
    vol.Optional(ATTR_NOTE): cv.string,
    vol.Optional(ATTR_COST): vol.All(vol.Coerce(float), vol.Range(min=0)),
})
DELETE_SCHEMA = vol.Schema({vol.Required(ATTR_ITEM_ID): cv.string, vol.Required(ATTR_EVENT_ID): cv.string})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not hass.data.get(CARD_REGISTERED):
        await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(CARD_PATH), False)])
        hass.data[CARD_REGISTERED] = True

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

    async def configure_item(call: ServiceCall) -> None:
        item_id = call.data[ATTR_ITEM_ID]
        await store.async_configure_item(
            item_id=item_id,
            name=call.data[ATTR_NAME],
            **{key: value for key, value in call.data.items() if key not in {ATTR_ITEM_ID, ATTR_NAME}},
        )
        hass.bus.async_fire(EVENT_MAINTENANCE_UPDATED, {"item_id": item_id, "action": "configured"})

    async def record_maintenance(call: ServiceCall) -> dict[str, str]:
        meter_entity = call.data.get(ATTR_METER_ENTITY)
        if not meter_entity:
            configured = store.items.get(call.data[ATTR_ITEM_ID])
            meter_entity = configured.meter_entity if configured else None
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
        item_id = call.data[ATTR_ITEM_ID]
        event = await store.async_record(
            item_id=item_id,
            name=call.data[ATTR_NAME],
            meter_value=meter_value,
            meter_entity=meter_entity,
            meter_unit=meter_unit,
            note=call.data.get(ATTR_NOTE),
            cost=call.data.get(ATTR_COST),
        )
        hass.bus.async_fire(EVENT_MAINTENANCE_UPDATED, {"item_id": item_id, "event_id": event.event_id, "action": "created"})
        return {"item_id": item_id, "event_id": event.event_id}

    async def delete_maintenance(call: ServiceCall) -> None:
        item_id = call.data[ATTR_ITEM_ID]
        event_id = call.data[ATTR_EVENT_ID]
        if not await store.async_delete_event(item_id, event_id):
            raise HomeAssistantError("Underhållsposten finns inte längre")
        hass.bus.async_fire(EVENT_MAINTENANCE_UPDATED, {"item_id": item_id, "event_id": event_id, "action": "deleted"})

    hass.services.async_register(DOMAIN, SERVICE_SET_WATER_BASELINE, set_water_baseline, schema=BASELINE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CONFIGURE_ITEM, configure_item, schema=CONFIGURE_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_RECORD_MAINTENANCE,
        record_maintenance,
        schema=RECORD_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(DOMAIN, SERVICE_DELETE_MAINTENANCE, delete_maintenance, schema=DELETE_SCHEMA)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_frontend(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            for service in (SERVICE_SET_WATER_BASELINE, SERVICE_CONFIGURE_ITEM, SERVICE_RECORD_MAINTENANCE, SERVICE_DELETE_MAINTENANCE):
                hass.services.async_remove(DOMAIN, service)
    return unloaded
