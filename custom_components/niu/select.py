"""Charging-speed select entity for the Niu integration."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NiuDataUpdateCoordinator
from .entity import NiuEntity

_LOGGER = logging.getLogger(__name__)


def _gear_label(index: int, total: int, gear: dict) -> str:
    """Build a human-friendly label for one charging-speed gear.

    Mirrors the Niu app: the slowest and fastest gears are labelled as such,
    and anything in between is labelled by its amperage.
    """
    if index == 0:
        return "Slow"
    if index == total - 1:
        return "Fast"
    power = gear.get("power")
    return f"{power}A" if power else f"Gear {index + 1}"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NiuDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.api.supports_charge_power():
        async_add_entities([NiuChargeSpeedSelect(coordinator)])


class NiuChargeSpeedSelect(NiuEntity, SelectEntity):
    """Selects how fast the scooter charges its battery.

    Only created for scooters that report at least two discrete charging-speed
    gears; scooters that only expose a continuous amperage range aren't
    supported by this entity.
    """

    _attr_name = "Charging Speed"
    _attr_icon = "mdi:ev-station"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NiuDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "charge_power")
        self._label_to_value: dict[str, str] = {}
        self._value_to_label: dict[str, str] = {}
        self._update_from_data()

    def _update_from_data(self) -> None:
        gears = self.api.charge_power_gears
        self._label_to_value = {
            _gear_label(index, len(gears), gear): gear["power"]
            for index, gear in enumerate(gears)
            if gear.get("power")
        }
        self._value_to_label = {
            value: label for label, value in self._label_to_value.items()
        }
        self._attr_options = list(self._label_to_value)
        current = self.api.charge_power_current
        self._attr_current_option = self._value_to_label.get(current)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_data()
        super()._handle_coordinator_update()

    async def async_select_option(self, option: str) -> None:
        value = self._label_to_value.get(option)
        if value is None:
            _LOGGER.error("Unknown charging speed option: %s", option)
            return
        await self.hass.async_add_executor_job(self.api.set_charge_power, value)
        self._attr_current_option = option
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
