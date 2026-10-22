"""iAquaLink Plus: salt cell (SWC) control on top of the core iAquaLink integration.

This integration does not log in on its own. It reuses the authenticated
iAquaLink session that the built-in ``iaqualink`` integration already holds and
sends the documented iQ20 salt cell commands (get_swc_config, set_swc_config,
control_swc_boost) that the core integration does not expose yet.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CORE_DOMAIN
from .coordinator import SwcCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

type PlusConfigEntry = ConfigEntry[dict[str, SwcCoordinator]]


def _core_entry(hass: HomeAssistant) -> ConfigEntry | None:
    entries = hass.config_entries.async_entries(CORE_DOMAIN)
    return entries[0] if entries else None


async def async_setup_entry(hass: HomeAssistant, entry: PlusConfigEntry) -> bool:
    core = _core_entry(hass)
    if core is None:
        raise ConfigEntryNotReady("The Jandy iAquaLink integration is not set up")
    if core.state is not ConfigEntryState.LOADED or getattr(core, "runtime_data", None) is None:
        raise ConfigEntryNotReady("Waiting for the Jandy iAquaLink integration to load")

    coordinators: dict[str, SwcCoordinator] = {}
    for serial, core_coord in core.runtime_data.coordinators.items():
        system = core_coord.system
        if getattr(system, "NAME", "") != "iaqua":
            _LOGGER.debug("Skipping non-iQ20 system %s (%s)", serial, getattr(system, "NAME", "?"))
            continue
        coord = SwcCoordinator(hass, entry, system)
        await coord.async_config_entry_first_refresh()
        coordinators[serial] = coord

    if not coordinators:
        raise ConfigEntryNotReady("No iQ20 (iAquaLink 2.0/3.0) systems found")

    entry.runtime_data = coordinators

    # The core integration owns the login. If it reloads, its system objects
    # are replaced, so reload this entry to pick up the new session.
    def _core_changed() -> None:
        if core.state is not ConfigEntryState.LOADED or core.runtime_data is None:
            return
        for serial, coord in coordinators.items():
            new = core.runtime_data.coordinators.get(serial)
            if new is None or new.system is not coord.system:
                hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))
                return

    entry.async_on_unload(core.async_on_state_change(_core_changed))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PlusConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
