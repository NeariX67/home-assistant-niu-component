"""Remote wake-up switch for the Niu integration."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NiuDataUpdateCoordinator
from .entity import NiuEntity
from .util import is_truthy_flag

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NiuDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NiuWakeSwitch(coordinator)])


class NiuWakeSwitch(NiuEntity, SwitchEntity):
    """Remotely wakes up / unlocks the scooter (turn on) or powers it back down (turn off)."""

    _attr_name = "Wake"
    _attr_icon = "mdi:motorbike-electric"

    def __init__(self, coordinator: NiuDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "wake")
        self._update_from_data()

    def _update_from_data(self) -> None:
        self._attr_is_on = is_truthy_flag(self.api.data_moto.get("isAccOn"))

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_data()
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self.api.wake_up)
        self._attr_is_on = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self.api.sleep)
        self._attr_is_on = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
