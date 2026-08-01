from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_BLADE_INTERVAL_HOURS,
    CONF_BLADE_USAGE_ENTITY,
    CONF_BLADE_WARNING_ENTITY,
    CONF_WATER_INSTALLATION_DATE,
    CONF_WATER_SOURCE_ENTITY,
    DEFAULT_BLADE_INTERVAL_HOURS,
    DOMAIN,
)


class BlomsterMaintenanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Blomster Underhåll."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return BlomsterMaintenanceOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create the single integration entry."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Blomster Underhåll", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_WATER_SOURCE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_WATER_INSTALLATION_DATE): selector.DateSelector(),
                vol.Required(
                    CONF_BLADE_USAGE_ENTITY,
                    default="sensor.garden_hugo_ii_luba_vpqnssl9_bladanvandningstid",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_BLADE_WARNING_ENTITY,
                    default="sensor.garden_hugo_ii_luba_vpqnssl9_bladslitagevarningstid",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_BLADE_INTERVAL_HOURS,
                    default=DEFAULT_BLADE_INTERVAL_HOURS,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="h",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema)


class BlomsterMaintenanceOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_WATER_SOURCE_ENTITY, default=current[CONF_WATER_SOURCE_ENTITY]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_WATER_INSTALLATION_DATE, default=current[CONF_WATER_INSTALLATION_DATE]): selector.DateSelector(),
                vol.Required(CONF_BLADE_USAGE_ENTITY, default=current[CONF_BLADE_USAGE_ENTITY]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_BLADE_WARNING_ENTITY, default=current[CONF_BLADE_WARNING_ENTITY]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_BLADE_INTERVAL_HOURS, default=current[CONF_BLADE_INTERVAL_HOURS]): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="h")
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
