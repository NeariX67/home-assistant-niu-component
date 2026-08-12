"""Charging-power and vehicle-volume number entities for the Niu integration."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NiuDataUpdateCoordinator
from .entity import NiuEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NiuDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NiuEntity] = []
    if coordinator.api.supports_charge_power():
        entities.append(NiuChargePowerNumber(coordinator))
    if coordinator.api.sound_volume_max:
        entities.append(NiuVolumeNumber(coordinator))
    async_add_entities(entities)


class NiuChargePowerNumber(NiuEntity, NumberEntity):
    """Sets the scooter's charging power to any value within its reported range.

    The API field is literally named "power" with no confirmed unit; it's
    presumably Watts (see `charge_power_range`/`set_charge_power`) but this
    isn't confirmed against the app's own UI.
    """

    _attr_name = "Charging Power"
    _attr_icon = "mdi:ev-station"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: NiuDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "charge_power")
        self._update_from_data()

    def _update_from_data(self) -> None:
        charge_power_range = self.api.charge_power_range
        if charge_power_range:
            self._attr_native_min_value = float(charge_power_range[0])
            self._attr_native_max_value = float(charge_power_range[1])
        current = self.api.charge_power_current
        self._attr_native_value = float(current) if current else None

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_data()
        super()._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        await self.hass.async_add_executor_job(self.api.set_charge_power, int(value))
        self._attr_native_value = int(value)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class NiuVolumeNumber(NiuEntity, NumberEntity):
    """Sets the scooter's horn/alert volume level."""

    _attr_name = "Volume"
    _attr_icon = "mdi:volume-high"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_step = 1

    def __init__(self, coordinator: NiuDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "volume")
        self._update_from_data()

    def _update_from_data(self) -> None:
        self._attr_native_max_value = self.api.sound_volume_max
        self._attr_native_value = self.api.sound_volume_current

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_data()
        super()._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        await self.hass.async_add_executor_job(self.api.set_volume, int(value))
        self._attr_native_value = int(value)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
