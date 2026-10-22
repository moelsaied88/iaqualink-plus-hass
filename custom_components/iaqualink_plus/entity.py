"""Base entity for iAquaLink Plus."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CORE_DOMAIN, DOMAIN
from .coordinator import SwcCoordinator


def _core_device_id(coordinator: SwcCoordinator) -> str | None:
    devices = dr.async_get(coordinator.hass).async_get_devices(
        identifiers={(CORE_DOMAIN, coordinator.serial)}
    )
    return devices[0].id if devices else None


class SwcEntity(CoordinatorEntity[SwcCoordinator]):
    _attr_has_entity_name = True
    requires_swc = True

    def __init__(self, coordinator: SwcCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_swc_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.serial}_swc")},
            via_device_id=_core_device_id(coordinator),
            manufacturer="Jandy",
            model="Salt water chlorinator (via iAquaLink)",
            name="Salt Cell",
        )

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        if not super().available or data is None:
            return False
        if self.requires_swc:
            return data.online and data.present
        return True
