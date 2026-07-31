from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import frontend, lovelace
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.components.lovelace.dashboard import DashboardsCollection, LovelaceStorage
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_URL = "/blomster_maintenance/blomster-maintenance-card.js?v=0.5.0"
CARD_URL_BASE = "/blomster_maintenance/blomster-maintenance-card.js"
DASHBOARD_URL_PATH = "blomster-underhall"
DASHBOARD_TITLE = "Blomster Underhåll"

DASHBOARD_CONFIG: dict[str, Any] = {
    "title": DASHBOARD_TITLE,
    "views": [
        {
            "title": "Servicebok",
            "path": "servicebok",
            "icon": "mdi:home-wrench",
            "type": "sections",
            "max_columns": 3,
            "sections": [
                {
                    "type": "grid",
                    "cards": [
                        {
                            "type": "markdown",
                            "title": "Digital servicebok",
                            "content": (
                                "Här samlas husets underhåll, serviceintervall, kostnader, "
                                "mätarställningar, dokument och påminnelser. Lägg till eller "
                                "uppdatera objekt med tjänsten "
                                "`blomster_maintenance.configure_item` och registrera utfört "
                                "underhåll med `blomster_maintenance.record_maintenance`."
                            ),
                        },
                        {
                            "type": "entities",
                            "title": "Översikt",
                            "show_header_toggle": False,
                            "entities": [
                                "sensor.servicebok",
                                "sensor.ackumulerad_vattenforbrukning",
                                "sensor.vatten_sedan_filterbyte",
                                "sensor.luba_blad_aterstaende_tid",
                                "binary_sensor.luba_blad_behover_bytas",
                            ],
                        },
                    ],
                },
                {
                    "type": "grid",
                    "cards": [
                        {
                            "type": "custom:blomster-maintenance-card",
                            "title": "Underhållshistorik",
                            "entities": [
                                "sensor.vattenfilter",
                                "sensor.luba_knivar",
                            ],
                            "max_rows": 20,
                            "show_delete": True,
                        }
                    ],
                },
                {
                    "type": "grid",
                    "cards": [
                        {
                            "type": "markdown",
                            "title": "Det här kan systemet",
                            "content": (
                                "- Egna underhållsobjekt för hela huset\n"
                                "- Intervall i dagar, liter, timmar eller starter\n"
                                "- Manualer, kvitton och bilder via länkar\n"
                                "- Kostnadslogg och årssammanställning\n"
                                "- Automatisk status och påminnelser\n"
                                "- Säker borttagning och ångring av historikposter"
                            ),
                        },
                        {
                            "type": "markdown",
                            "title": "Exempel på objekt",
                            "content": (
                                "Vattenfilter, IVT-värmepump, FTX, varmvattenberedare, "
                                "hängrännor, röklarm, Luba-knivar och andra komponenter kan "
                                "läggas in med egna serviceintervall och dokument."
                            ),
                        },
                    ],
                },
            ],
        }
    ],
}


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the card resource and example dashboard when Lovelace uses storage mode."""
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        _LOGGER.warning("Lovelace är inte laddat; resurs och standard-dashboard kunde inte skapas")
        return

    await _async_register_resource(lovelace_data.resources)
    await _async_register_dashboard(hass, lovelace_data)


async def _async_register_resource(resources: Any) -> None:
    """Create or update the custom-card resource in storage mode."""
    if not hasattr(resources, "async_create_item"):
        _LOGGER.warning(
            "Lovelace-resurser hanteras i YAML-läge; lägg till %s som module manuellt",
            CARD_URL,
        )
        return

    items = resources.async_items() if getattr(resources, "loaded", False) else []
    if not getattr(resources, "loaded", False) and hasattr(resources, "_async_ensure_loaded"):
        await resources._async_ensure_loaded()  # noqa: SLF001 - HA exposes no public loader
        items = resources.async_items()

    for item in items or []:
        url = str(item.get("url", ""))
        if url.split("?", 1)[0] != CARD_URL_BASE:
            continue
        if url != CARD_URL or item.get("type") != "module":
            await resources.async_update_item(
                item["id"], {"url": CARD_URL, "res_type": "module"}
            )
        return

    await resources.async_create_item({"url": CARD_URL, "res_type": "module"})


async def _async_register_dashboard(hass: HomeAssistant, lovelace_data: Any) -> None:
    """Create a storage dashboard and make it available immediately."""
    dashboards = DashboardsCollection(hass)
    await dashboards.async_load()

    item = next(
        (
            existing
            for existing in dashboards.async_items()
            if existing.get("url_path") == DASHBOARD_URL_PATH
        ),
        None,
    )
    if item is None:
        item = await dashboards.async_create_item(
            {
                "url_path": DASHBOARD_URL_PATH,
                "title": DASHBOARD_TITLE,
                "icon": "mdi:home-wrench",
                "show_in_sidebar": True,
                "require_admin": False,
            }
        )

    dashboard_store = lovelace_data.dashboards.get(DASHBOARD_URL_PATH)
    if dashboard_store is None:
        dashboard_store = LovelaceStorage(hass, item)
        lovelace_data.dashboards[DASHBOARD_URL_PATH] = dashboard_store
        frontend.async_register_built_in_panel(
            hass,
            "lovelace",
            frontend_url_path=DASHBOARD_URL_PATH,
            require_admin=False,
            show_in_sidebar=True,
            sidebar_title=DASHBOARD_TITLE,
            sidebar_icon="mdi:home-wrench",
            config={"mode": MODE_STORAGE},
        )

    try:
        await dashboard_store.async_load(False)
    except Exception:  # Dashboard is new and has no config yet.
        await dashboard_store.async_save(DASHBOARD_CONFIG)
