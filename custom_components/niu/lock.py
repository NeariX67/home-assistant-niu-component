"""Remote anti-theft lock for the Niu integration."""
from __future__ import annotations

import logging

from homeassistant.components.lock import LockEntity
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
    async_add_entities([NiuFortificationLock(coordinator)])


class NiuFortificationLock(NiuEntity, LockEntity):
    """Arms/disarms the scooter's anti-theft alarm (Niu calls this "fortification").

    This is a different concept from the `lockStatus` field the diagnostic
    "Lock Status" sensor reports, which reflects the scooter's own electronic
    lock actuator rather than the remote anti-theft alarm system.
    """

    _attr_name = "Anti-Theft Lock"

    def __init__(self, coordinator: NiuDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "fortification")
        self._update_from_data()

    def _update_from_data(self) -> None:
        self._attr_is_locked = is_truthy_flag(self.api.data_moto.get("isFortificationOn"))

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_data()
        super()._handle_coordinator_update()

    @property
    def icon(self) -> str:
        return "mdi:lock" if self.is_locked else "mdi:lock-open"

    async def async_lock(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self.api.lock)
        self._attr_is_locked = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_unlock(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self.api.unlock)
        self._attr_is_locked = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
