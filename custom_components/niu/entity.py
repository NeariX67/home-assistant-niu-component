"""Base entity for the Niu integration."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NiuApi
from .const import DOMAIN
from .coordinator import NiuDataUpdateCoordinator


class NiuEntity(CoordinatorEntity[NiuDataUpdateCoordinator]):
    """Base class for all entities belonging to one Niu scooter.

    All entities for a given scooter are grouped under a single device,
    identified by the scooter's serial number (previously all scooters were
    incorrectly grouped under one shared, hardcoded device identifier).
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: NiuDataUpdateCoordinator, key: str) -> None:
        super().__init__(coordinator)
        api = coordinator.api
        self._attr_unique_id = f"{api.sn}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, api.sn)},
            name=api.sensor_prefix,
            manufacturer="Niu",
        )

    @property
    def api(self) -> NiuApi:
        return self.coordinator.api
