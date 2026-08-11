"""Last-trip thumbnail camera for the Niu integration."""
from __future__ import annotations

import logging
from typing import final

import httpx

from homeassistant.components.camera import CameraState
from homeassistant.components.generic.camera import GenericCamera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

from .const import DOMAIN
from .coordinator import NiuDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
GET_IMAGE_TIMEOUT = 10


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NiuDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    api = coordinator.api
    camera_name = f"{api.sensor_prefix} Last Track Camera"

    device_info = {
        "name": camera_name,
        "still_image_url": "",
        "stream_source": None,
        "username": None,
        "password": None,
        "content_type": "image/jpeg",
        "advanced": {
            "authentication": "basic",
            "limit_refetch_to_url_change": False,
            "framerate": 2,
            "verify_ssl": True,
        },
    }
    async_add_entities([LastTrackCamera(hass, coordinator, device_info, camera_name, camera_name)])


class LastTrackCamera(GenericCamera):
    """Shows a thumbnail image of the scooter's most recently completed trip."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: NiuDataUpdateCoordinator,
        device_info: dict,
        identifier: str,
        title: str,
    ) -> None:
        self._coordinator = coordinator
        super().__init__(hass, device_info, identifier, title)

    @property
    @final
    def state(self) -> str:
        """Return the camera state."""
        return CameraState.IDLE

    @property
    def is_on(self) -> bool:
        """Return true if on."""
        return self._last_image != b""

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        api = self._coordinator.api
        return DeviceInfo(
            identifiers={(DOMAIN, api.sn)},
            name=api.sensor_prefix,
            manufacturer="Niu",
        )

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        last_track_url = self._coordinator.api.data_last_track.get("track_thumb")
        if not last_track_url:
            return self._last_image

        if last_track_url == self._last_url and self._last_image:
            return self._last_image

        try:
            async_client = get_async_client(self.hass, verify_ssl=self.verify_ssl)
            response = await async_client.get(
                last_track_url, auth=self._auth, timeout=GET_IMAGE_TIMEOUT,
                follow_redirects=True,
            )
            response.raise_for_status()
            self._last_image = response.content
        except httpx.TimeoutException:
            _LOGGER.error("Timeout getting camera image from %s", self._name)
            return self._last_image
        except (httpx.RequestError, httpx.HTTPStatusError) as err:
            _LOGGER.error("Error getting new camera image from %s: %s", self._name, err)
            return self._last_image

        self._last_url = last_track_url
        return self._last_image
