"""Config flow for Frigate Device Merger."""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN


class FrigateDeviceMergerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Frigate Device Merger."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        # This integration doesn't need user input, just create the entry
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        
        return self.async_create_entry(title="Frigate Device Merger", data={})
