"""Data update coordinator for the Niu integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NiuApi, NiuApiError

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=10)


class NiuDataUpdateCoordinator(DataUpdateCoordinator[NiuApi]):
    """Fetches every Niu endpoint used by this integration in one polling pass.

    Entities read live values off `coordinator.api` (exposed via `NiuEntity.api`)
    rather than off `coordinator.data`, since the API client already holds the
    parsed response for each endpoint.
    """

    def __init__(self, hass: HomeAssistant, api: NiuApi) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=f"niu-{api.sn}",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> NiuApi:
        try:
            await self.hass.async_add_executor_job(self.api.update_all)
        except NiuApiError as err:
            raise UpdateFailed(str(err)) from err
        return self.api
