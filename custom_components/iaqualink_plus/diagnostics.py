"""Diagnostics: raw salt cell payloads plus read-only probes of other iQ20 features."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

TO_REDACT = {"serial", "serial_number", "response", "email", "username"}

# Read-only commands from the iQ20 protocol reference. Used to see what else this
# controller supports (OneTouch macros, variable-speed pump) before building it.
PROBES = ("get_onetouch", "get_vsp_names", "get_master_device_list")


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry) -> dict[str, Any]:
    systems = []
    for coord in entry.runtime_data.values():
        probes: dict[str, Any] = {}
        for command in PROBES:
            try:
                probes[command] = await coord._request(command)  # noqa: SLF001
            except Exception as err:  # noqa: BLE001
                probes[command] = f"error: {err}"
        data = coord.data
        systems.append(
            async_redact_data(
                {
                    "online": data.online if data else None,
                    "salt_cell_present": data.present if data else None,
                    "home": dict(data.home) if data else {},
                    "swc_config": dict(data.config) if data else {},
                    "probes": probes,
                },
                TO_REDACT,
            )
        )
    return {"systems": systems}
