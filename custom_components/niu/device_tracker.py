"""Device tracker platform for the Niu integration."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NiuDataUpdateCoordinator
from .entity import NiuEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Niu device tracker for one scooter."""
    coordinator: NiuDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NiuDeviceTracker(coordinator)])


class NiuDeviceTracker(NiuEntity, TrackerEntity):
    """Reports the scooter's last known GPS position."""

    _attr_name = "Location"
    _attr_icon = "mdi:motorbike-electric"

    def __init__(self, coordinator: NiuDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "location")

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self.api.data_moto.get("postion", {}).get("lat")

    @property
    def longitude(self) -> float | None:
        return self.api.data_moto.get("postion", {}).get("lng")
