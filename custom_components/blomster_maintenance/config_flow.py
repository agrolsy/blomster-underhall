from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

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
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Blomster Underhåll", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_WATER_SOURCE_ENTITY): cv.entity_id,
                vol.Required(CONF_WATER_INSTALLATION_DATE): cv.date,
                vol.Required(
                    CONF_BLADE_USAGE_ENTITY,
                    default="sensor.garden_hugo_ii_luba_vpqnssl9_bladanvandningstid",
                ): cv.entity_id,
                vol.Required(
                    CONF_BLADE_WARNING_ENTITY,
                    default="sensor.garden_hugo_ii_luba_vpqnssl9_bladslitagevarningstid",
                ): cv.entity_id,
                vol.Required(
                    CONF_BLADE_INTERVAL_HOURS,
                    default=DEFAULT_BLADE_INTERVAL_HOURS,
                ): vol.All(vol.Coerce(float), vol.Range(min=1)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
