from __future__ import annotations

from datetime import timedelta

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .sensor import _item_status
from .storage import MaintenanceStore


async def async_start_reminders(hass: HomeAssistant, store: MaintenanceStore):
    """Create stable persistent reminders for due service-book items."""

    @callback
    def refresh(_now=None) -> None:
        active_ids: set[str] = set()
        for item in store.items.values():
            status = _item_status(hass, item)["status"]
            notification_id = f"blomster_maintenance_{item.item_id}"
            if status not in {"due_soon", "overdue", "never"}:
                persistent_notification.async_dismiss(hass, notification_id)
                continue
            active_ids.add(notification_id)
            heading = {
                "overdue": "Underhåll är försenat",
                "due_soon": "Underhåll närmar sig",
                "never": "Underhåll är inte registrerat",
            }[status]
            persistent_notification.async_create(
                hass,
                f"{item.name}: {heading.lower()}.",
                title=heading,
                notification_id=notification_id,
            )

    refresh()
    return async_track_time_interval(hass, refresh, timedelta(hours=1))
