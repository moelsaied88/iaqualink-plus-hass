"""Salt cell binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import SwcEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    entities = []
    for coord in entry.runtime_data.values():
        entities += [LowSaltSensor(coord), BoostEnabledSensor(coord)]
    async_add_entities(entities)


class LowSaltSensor(SwcEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:shaker-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "low_salt")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.low_salt


class BoostEnabledSensor(SwcEntity, BinarySensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:dip-switch"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "boost_hardware_enabled")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.boost_hardware_enabled
