"""Salt cell output and boost-duration numbers."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import SwcEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    entities = []
    for coord in entry.runtime_data.values():
        entities += [
            OutputNumber(coord, "pool_output_setting", pool=True),
            OutputNumber(coord, "spa_output_setting", pool=False),
            BoostHoursNumber(coord),
        ]
    async_add_entities(entities)


class OutputNumber(SwcEntity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:knob"

    def __init__(self, coordinator, key: str, pool: bool) -> None:
        super().__init__(coordinator, key)
        self._pool = pool
        if not pool:
            self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | None:
        d = self.coordinator.data
        return d.pool_set_point if self._pool else d.spa_set_point

    async def async_set_native_value(self, value: float) -> None:
        if self._pool:
            await self.coordinator.async_set_output(pool=int(value))
        else:
            await self.coordinator.async_set_output(spa=int(value))


class BoostHoursNumber(SwcEntity, RestoreNumber):
    """Duration used the next time boost is started (kept locally)."""

    _attr_native_min_value = 1
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-cog-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "boost_hours")
        self._value: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last and last.native_value is not None:
            self._value = last.native_value

    @property
    def native_value(self) -> float:
        if self._value is not None:
            return self._value
        return float(self.coordinator.data.boost_hours_setting or 24)

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        self.async_write_ha_state()
