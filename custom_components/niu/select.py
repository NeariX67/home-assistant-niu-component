"""Charging-limit select entity for the Niu integration."""
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


# Confirmed from the Niu app's own UI; the align endpoint doesn't enumerate these.
CHARGE_LIMIT_OPTIONS = ("80", "85", "90", "95", "100")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NiuDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.api.supports_charging_limit():
        async_add_entities([NiuChargeLimitSelect(coordinator)])


class NiuChargeLimitSelect(NiuEntity, SelectEntity):
    """Caps how full the scooter is allowed to charge its battery, as a percentage."""

    _attr_name = "Charging Limit"
    _attr_icon = "mdi:battery-charging-high"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(CHARGE_LIMIT_OPTIONS)

    def __init__(self, coordinator: NiuDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "charging_limit")
        self._update_from_data()

    def _update_from_data(self) -> None:
        self._attr_current_option = self.api.charging_limit_current

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_data()
        super()._handle_coordinator_update()

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(self.api.set_charging_limit, option)
        self._attr_current_option = option
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
