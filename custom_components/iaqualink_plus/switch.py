"""Salt cell boost switch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BOOST_ACTIVE_STATES, DOMAIN
from .entity import SwcEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(BoostSwitch(coord) for coord in entry.runtime_data.values())


class BoostSwitch(SwcEntity, SwitchEntity):
    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "boost")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.boost_status in BOOST_ACTIVE_STATES

    def _boost_hours(self) -> int:
        registry = er.async_get(self.hass)
        hours_id = registry.async_get_entity_id(
            "number", DOMAIN, f"{self.coordinator.serial}_swc_boost_hours"
        )
        state = self.hass.states.get(hours_id) if hours_id else None
        try:
            return max(1, min(24, int(float(state.state)))) if state else 24
        except (TypeError, ValueError):
            return 24

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.coordinator.data.boost_status == "paused":
            await self.coordinator.async_boost("resume")
        else:
            await self.coordinator.async_boost("start", hours=self._boost_hours(), mode=self.coordinator.data.boost_mode or "pool")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_boost("stop")
