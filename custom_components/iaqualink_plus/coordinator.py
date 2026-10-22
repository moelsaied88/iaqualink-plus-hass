"""Coordinator that reads the salt cell data the core integration ignores."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from iaqualink.exception import (
    AqualinkServiceException,
    AqualinkServiceThrottledException,
    AqualinkServiceUnauthorizedException,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CMD_CONTROL_SWC_BOOST,
    CMD_GET_HOME,
    CMD_GET_SWC_CONFIG,
    CMD_SET_SWC_CONFIG,
    DOMAIN,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def flatten_home(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten the get_home 'home_screen' list of single-key dicts."""
    home: dict[str, Any] = {}
    for item in payload.get("home_screen", []) or []:
        if isinstance(item, dict):
            home.update(item)
    return home


@dataclass
class SwcData:
    """Parsed salt cell state."""

    online: bool = False
    present: bool = False
    home: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def info(self) -> dict[str, Any]:
        info = self.home.get("swc_info")
        return info if isinstance(info, dict) else {}

    @property
    def pool_set_point(self) -> int | None:
        value = _to_int(self.config.get("poolSWCSP"))
        return value if value is not None else _to_int(self.home.get("swc_set_point"))

    @property
    def spa_set_point(self) -> int | None:
        return _to_int(self.config.get("spaSWCSP"))

    @property
    def pool_output(self) -> int | None:
        return _to_int(self.info.get("swcPoolValue"))

    @property
    def spa_output(self) -> int | None:
        return _to_int(self.info.get("swcSpaValue"))

    @property
    def pool_status(self) -> str | None:
        return (self.info.get("swcPoolStatus") or None) and str(self.info["swcPoolStatus"]).lower()

    @property
    def spa_status(self) -> str | None:
        return (self.info.get("swcSpaStatus") or None) and str(self.info["swcSpaStatus"]).lower()

    @property
    def boost_status(self) -> str:
        status = self.config.get("boostStatus")
        if status:
            return str(status).lower()
        return "on" if str(self.home.get("swc_boost")) == "1" else "off"

    @property
    def boost_hours_setting(self) -> int | None:
        return _to_int(self.config.get("boostHrsVal"))

    @property
    def boost_remaining_minutes(self) -> int | None:
        hrs = _to_int(self.config.get("remainingBoostHrs"))
        mins = _to_int(self.config.get("remainingBoostMins"))
        if hrs is None and mins is None:
            return None
        return (hrs or 0) * 60 + (mins or 0)

    @property
    def boost_mode(self) -> str | None:
        return self.config.get("boostMode") or None

    @property
    def boost_hardware_enabled(self) -> bool | None:
        raw = self.config.get("boostDipSwitch")
        if raw in (None, ""):
            return None
        return str(raw).lower() == "on"

    @property
    def low_salt(self) -> bool | None:
        raw = self.home.get("swc_low")
        if raw in (None, ""):
            return None
        return str(raw) == "1"

    @property
    def pool_salinity(self) -> int | None:
        return _to_int(self.home.get("pool_salinity"))

    @property
    def spa_salinity(self) -> int | None:
        return _to_int(self.home.get("spa_salinity"))


class SwcCoordinator(DataUpdateCoordinator[SwcData]):
    """Polls get_home + get_swc_config for one iQ20 system."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, system: Any) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{system.serial}",
            update_interval=UPDATE_INTERVAL,
        )
        self.system = system

    @property
    def serial(self) -> str:
        return self.system.serial

    async def _request(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self.system._send_session_request(command, dict(params or {}))  # noqa: SLF001
        data = response.json()
        if not isinstance(data, dict):
            raise UpdateFailed(f"Unexpected {command} response: {data!r}")
        return data

    async def _async_update_data(self) -> SwcData:
        previous = self.data or SwcData()
        try:
            home_payload = await self._request(CMD_GET_HOME)
            home = flatten_home(home_payload)
            online = str(home.get("status", "")).lower() == "online"
            info = home.get("swc_info")
            present = bool(
                (isinstance(info, dict) and info.get("isswcPresent"))
                or str(home.get("swc_set_point", "")).strip() != ""
            )
            config = previous.config
            if present and online:
                config = await self._request(CMD_GET_SWC_CONFIG)
        except AqualinkServiceThrottledException:
            _LOGGER.debug("iAquaLink throttled salt cell poll; keeping last data")
            return previous
        except AqualinkServiceUnauthorizedException as err:
            raise UpdateFailed("iAquaLink login expired; the core integration will re-authenticate") from err
        except (AqualinkServiceException, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Salt cell poll failed: {err}") from err
        except Exception as err:  # httpx errors differ across HA versions
            raise UpdateFailed(f"Salt cell poll failed: {err}") from err
        return SwcData(online=online, present=present, home=home, config=config)

    async def _write(self, command: str, params: dict[str, Any]) -> None:
        try:
            result = await self._request(command, params)
        except Exception as err:
            raise HomeAssistantError(f"iAquaLink rejected {command}: {err}") from err
        if result.get("is_error") or str(result.get("response", "success")).lower() not in ("success", ""):
            raise HomeAssistantError(f"iAquaLink {command} failed: {result.get('response')}")
        if self.data is not None:
            merged = {**self.data.config, **result}
            self.async_set_updated_data(
                SwcData(online=self.data.online, present=self.data.present, home=self.data.home, config=merged)
            )
        await self.async_request_refresh()

    async def async_set_output(self, pool: int | None = None, spa: int | None = None) -> None:
        current = self.data or SwcData()
        pool_sp = pool if pool is not None else (current.pool_set_point or 0)
        spa_sp = spa if spa is not None else (current.spa_set_point or 0)
        await self._write(CMD_SET_SWC_CONFIG, {"poolswcsp": int(pool_sp), "spaswcsp": int(spa_sp)})

    async def async_boost(self, control: str, hours: int | None = None, mode: str = "pool") -> None:
        params: dict[str, Any] = {"boostcontrol": control}
        if control == "start":
            params["boosthrs"] = int(hours or 24)
            params["boostmode"] = mode
        await self._write(CMD_CONTROL_SWC_BOOST, params)
