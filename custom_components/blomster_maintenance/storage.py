from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


@dataclass(slots=True)
class MaintenanceEvent:
    event_id: str
    performed_at: str
    meter_value: float | None = None
    meter_entity: str | None = None
    meter_unit: str | None = None
    note: str | None = None


@dataclass(slots=True)
class MaintenanceItem:
    item_id: str
    name: str
    events: list[MaintenanceEvent] = field(default_factory=list)


@dataclass(slots=True)
class WaterAccumulator:
    source_entity: str | None = None
    installation_date: str | None = None
    accumulated_liters: float = 0.0
    last_source_value: float | None = None
    last_updated: str | None = None


class MaintenanceStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.water = WaterAccumulator()
        self.items: dict[str, MaintenanceItem] = {}

    async def async_load(self) -> None:
        raw = await self._store.async_load() or {}
        self.water = WaterAccumulator(**raw.get("water", {}))
        migrated = False
        items: dict[str, MaintenanceItem] = {}
        for item in raw.get("items", []):
            events: list[MaintenanceEvent] = []
            for event in item.get("events", []):
                event_data = dict(event)
                if not event_data.get("event_id"):
                    event_data["event_id"] = uuid4().hex
                    migrated = True
                events.append(MaintenanceEvent(**event_data))
            items[item["item_id"]] = MaintenanceItem(
                item_id=item["item_id"],
                name=item["name"],
                events=events,
            )
        self.items = items
        if migrated:
            await self.async_save()

    async def async_save(self) -> None:
        await self._store.async_save(
            {
                "water": asdict(self.water),
                "items": [asdict(item) for item in self.items.values()],
            }
        )

    async def async_configure_water(self, source_entity: str, installation_date: str) -> None:
        self.water.source_entity = source_entity
        self.water.installation_date = installation_date
        await self.async_save()

    async def async_set_baseline(self, baseline_liters: float, current_source_value: float | None) -> None:
        self.water.accumulated_liters = baseline_liters
        self.water.last_source_value = current_source_value
        self.water.last_updated = datetime.now().astimezone().isoformat()
        await self.async_save()

    async def async_add_source_value(self, value: float) -> bool:
        previous = self.water.last_source_value
        if previous is None:
            self.water.last_source_value = value
        else:
            delta = value - previous if value >= previous else value
            if delta < 0:
                return False
            self.water.accumulated_liters += delta
            self.water.last_source_value = value
        self.water.last_updated = datetime.now().astimezone().isoformat()
        await self.async_save()
        return True

    async def async_record(
        self,
        item_id: str,
        name: str,
        meter_value: float | None,
        meter_entity: str | None,
        meter_unit: str | None,
        note: str | None,
    ) -> MaintenanceEvent:
        item = self.items.get(item_id) or MaintenanceItem(item_id=item_id, name=name)
        item.name = name
        event = MaintenanceEvent(
            event_id=uuid4().hex,
            performed_at=datetime.now().astimezone().isoformat(),
            meter_value=meter_value,
            meter_entity=meter_entity,
            meter_unit=meter_unit,
            note=note,
        )
        item.events.append(event)
        self.items[item_id] = item
        await self.async_save()
        return event

    async def async_delete_event(self, item_id: str, event_id: str) -> bool:
        item = self.items.get(item_id)
        if item is None:
            return False
        remaining = [event for event in item.events if event.event_id != event_id]
        if len(remaining) == len(item.events):
            return False
        item.events = remaining
        await self.async_save()
        return True
