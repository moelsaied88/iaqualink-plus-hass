"""Salt cell sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION, PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SWC_STATUSES
from .coordinator import SwcData
from .entity import SwcEntity


@dataclass(frozen=True, kw_only=True)
class SwcSensorDescription(SensorEntityDescription):
    value_fn: Callable[[SwcData], Any]
    requires_swc: bool = True


def _status(value: str | None) -> str | None:
    if value is None:
        return None
    return value if value in SWC_STATUSES else "unknown"


SENSORS: tuple[SwcSensorDescription, ...] = (
    SwcSensorDescription(
        key="pool_output",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-percent",
        value_fn=lambda d: d.pool_output,
    ),
    SwcSensorDescription(
        key="pool_status",
        device_class=SensorDeviceClass.ENUM,
        options=SWC_STATUSES,
        icon="mdi:flask-round-bottom",
        value_fn=lambda d: _status(d.pool_status),
    ),
    SwcSensorDescription(
        key="spa_output",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.spa_output,
    ),
    SwcSensorDescription(
        key="spa_status",
        device_class=SensorDeviceClass.ENUM,
        options=SWC_STATUSES,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _status(d.spa_status),
    ),
    SwcSensorDescription(
        key="salinity",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shaker-outline",
        value_fn=lambda d: d.pool_salinity,
    ),
    SwcSensorDescription(
        key="boost_status",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "on", "paused"],
        icon="mdi:rocket-launch",
        value_fn=lambda d: d.boost_status if d.boost_status in ("off", "on", "paused") else "off",
    ),
    SwcSensorDescription(
        key="boost_remaining",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:timer-sand",
        value_fn=lambda d: d.boost_remaining_minutes,
    ),
    SwcSensorDescription(
        key="detected",
        device_class=SensorDeviceClass.ENUM,
        options=["detected", "not_detected", "controller_offline"],
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_swc=False,
        value_fn=lambda d: "controller_offline" if not d.online else ("detected" if d.present else "not_detected"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(
        SwcSensor(coord, desc) for coord in entry.runtime_data.values() for desc in SENSORS
    )


class SwcSensor(SwcEntity, SensorEntity):
    entity_description: SwcSensorDescription

    def __init__(self, coordinator, description: SwcSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self.requires_swc = description.requires_swc

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)
