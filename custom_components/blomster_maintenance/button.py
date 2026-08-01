from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, EVENT_MAINTENANCE_UPDATED
from .sensor import _item_problem_signature
from .storage import MaintenanceStore


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    store: MaintenanceStore = hass.data[DOMAIN][entry.entry_id]
    entities: dict[str, MaintenanceAcknowledgeButton] = {}

    @callback
    def sync_items(_event: Event | None = None) -> None:
        new_entities = []
        for item_id in store.items:
            if item_id not in entities:
                entities[item_id] = MaintenanceAcknowledgeButton(hass, store, item_id)
                new_entities.append(entities[item_id])
        if new_entities:
            async_add_entities(new_entities)

    sync_items()
    entry.async_on_unload(hass.bus.async_listen(EVENT_MAINTENANCE_UPDATED, sync_items))


class MaintenanceAcknowledgeButton(ButtonEntity):
    _attr_icon = "mdi:check-decagram"

    def __init__(self, hass: HomeAssistant, store: MaintenanceStore, item_id: str) -> None:
        self.hass = hass
        self._store = store
        self._item_id = item_id
        self._attr_unique_id = f"{DOMAIN}_{item_id}_acknowledge"

    @property
    def name(self) -> str:
        return f"Kvittera {self._store.items[self._item_id].name}"

    async def async_press(self) -> None:
        item = self._store.items[self._item_id]
        signature = _item_problem_signature(self.hass, item)
        if signature:
            await self._store.async_acknowledge_item(self._item_id, signature)
            self.hass.bus.async_fire(EVENT_MAINTENANCE_UPDATED, {"item_id": self._item_id, "action": "acknowledged"})
