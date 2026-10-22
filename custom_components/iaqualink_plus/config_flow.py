"""Config flow for iAquaLink Plus."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CORE_DOMAIN, DOMAIN


class IaqualinkPlusConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not self.hass.config_entries.async_entries(CORE_DOMAIN):
            return self.async_abort(reason="core_missing")
        if user_input is not None:
            return self.async_create_entry(title="iAquaLink Salt Cell", data={})
        return self.async_show_form(step_id="user")
