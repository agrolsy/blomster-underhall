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
    cost: float | None = None


@dataclass(slots=True)
class MaintenanceItem:
    item_id: str
    name: str
    category: str | None = None
    location: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    installed_at: str | None = None
    interval_type: str | None = None
    interval_value: float | None = None
    meter_entity: str | None = None
    manual_url: str | None = None
    receipt_url: str | None = None
    image_url: str | None = None
    warning_entities: list[str] = field(default_factory=list)
    acknowledged_signature: str | None = None
    events: list[MaintenanceEvent] = field(default_factory=list)


@dataclass(slots=True)
class WaterAccumulator:
    source_entity: str | None = None
    installation_date: str | None = None
    accumulated_liters: float = 0.0
    last_source_value: float | None = None
    last_updated: str | None = None
    baseline_established: bool = False
    imported_from_recorder: bool = False


class MaintenanceStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.water = WaterAccumulator()
        self.items: dict[str, MaintenanceItem] = {}

    async def async_load(self) -> None:
        raw = await self._store.async_load() or {}
        water_data = dict(raw.get("water", {}))
        water_data.setdefault("baseline_established", bool(water_data.get("accumulated_liters", 0)))
        water_data.setdefault("imported_from_recorder", False)
        self.water = WaterAccumulator(**water_data)
        migrated = False
        items: dict[str, MaintenanceItem] = {}
        for raw_item in raw.get("items", []):
            item_data = dict(raw_item)
            raw_events = item_data.pop("events", [])
            events: list[MaintenanceEvent] = []
            for raw_event in raw_events:
                event_data = dict(raw_event)
                if not event_data.get("event_id"):
                    event_data["event_id"] = uuid4().hex
                    migrated = True
                event_data.setdefault("cost", None)
                events.append(MaintenanceEvent(**event_data))
            item_data.setdefault("category", None)
            item_data.setdefault("location", None)
            item_data.setdefault("manufacturer", None)
            item_data.setdefault("model", None)
            item_data.setdefault("serial_number", None)
            item_data.setdefault("installed_at", None)
            item_data.setdefault("interval_type", None)
            item_data.setdefault("interval_value", None)
            item_data.setdefault("meter_entity", None)
            item_data.setdefault("manual_url", None)
            item_data.setdefault("receipt_url", None)
            item_data.setdefault("image_url", None)
            item_data.setdefault("warning_entities", [])
            item_data.setdefault("acknowledged_signature", None)
            items[item_data["item_id"]] = MaintenanceItem(**item_data, events=events)
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
        self.water.baseline_established = True
        self.water.imported_from_recorder = False
        await self.async_save()

    async def async_set_imported_total(self, total: float, current_source_value: float) -> None:
        self.water.accumulated_liters = total
        self.water.last_source_value = current_source_value
        self.water.last_updated = datetime.now().astimezone().isoformat()
        self.water.baseline_established = True
        self.water.imported_from_recorder = True
        await self.async_save()

    async def async_add_source_value(self, value: float) -> bool:
        previous = self.water.last_source_value
        if previous is None:
            self.water.last_source_value = value
        elif not self.water.baseline_established:
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

    async def async_acknowledge_item(self, item_id: str, signature: str) -> bool:
        item = self.items.get(item_id)
        if item is None:
            return False
        item.acknowledged_signature = signature
        await self.async_save()
        return True

    async def async_configure_item(self, item_id: str, name: str, **values: Any) -> MaintenanceItem:
        item = self.items.get(item_id) or MaintenanceItem(item_id=item_id, name=name)
        item.name = name
        for key, value in values.items():
            if hasattr(item, key):
                setattr(item, key, value)
        self.items[item_id] = item
        await self.async_save()
        return item

    async def async_record(
        self,
        item_id: str,
        name: str,
        meter_value: float | None,
        meter_entity: str | None,
        meter_unit: str | None,
        note: str | None,
        cost: float | None = None,
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
            cost=cost,
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
