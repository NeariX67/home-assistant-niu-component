"""Binary sensor platform for the Niu integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import NiuApi
from .const import DOMAIN
from .coordinator import NiuDataUpdateCoordinator
from .entity import NiuEntity
from .util import is_truthy_flag


@dataclass(frozen=True, kw_only=True)
class NiuBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Niu binary sensor sourced from one field of the Niu cloud API."""

    value_fn: Callable[[NiuApi], bool]
    exists_fn: Callable[[NiuApi], bool] = lambda api: True


def _battery_binary_sensors(compartment: str) -> list[NiuBinarySensorEntityDescription]:
    return [
        NiuBinarySensorEntityDescription(
            key=f"battery_{compartment.lower()}_connected",
            name=f"Battery {compartment} Connected",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda api, c=compartment: bool(api.battery(c).get("isConnected")),
        ),
    ]


# (field, display name, device class, entity category)
_WHEEL_STATUS_FIELDS: tuple[
    tuple[str, str, BinarySensorDeviceClass | None, EntityCategory | None], ...
] = (
    ("power_low", "Sensor Battery Low", BinarySensorDeviceClass.BATTERY, EntityCategory.DIAGNOSTIC),
    ("pressure_low", "Pressure Low", BinarySensorDeviceClass.PROBLEM, None),
    ("pressure_high", "Pressure High", BinarySensorDeviceClass.PROBLEM, None),
    ("temperature_low", "Temperature Low", BinarySensorDeviceClass.COLD, None),
    ("temperature_high", "Temperature High", BinarySensorDeviceClass.HEAT, None),
    ("leak", "Leak Detected", BinarySensorDeviceClass.PROBLEM, None),
    (
        "communication_failure",
        "Communication Failure",
        BinarySensorDeviceClass.PROBLEM,
        EntityCategory.DIAGNOSTIC,
    ),
    ("connected", "Sensor Connected", BinarySensorDeviceClass.CONNECTIVITY, EntityCategory.DIAGNOSTIC),
)


def _wheel_binary_sensors(wheel: str, label: str) -> list[NiuBinarySensorEntityDescription]:
    """Build TPMS binary sensors for one wheel. Only created if it's actually paired."""

    def paired(api: NiuApi, w=wheel) -> bool:
        return bool(api.data_moto.get(f"{w}_wheel_status", {}).get("paired"))

    return [
        NiuBinarySensorEntityDescription(
            key=f"{wheel}_wheel_{field}",
            name=f"{label} Wheel {name}",
            device_class=device_class,
            entity_category=category,
            exists_fn=paired,
            value_fn=lambda api, w=wheel, f=field: bool(
                api.data_moto.get(f"{w}_wheel_status", {}).get(f)
            ),
        )
        for field, name, device_class, category in _WHEEL_STATUS_FIELDS
    ]


BINARY_SENSORS: tuple[NiuBinarySensorEntityDescription, ...] = (
    NiuBinarySensorEntityDescription(
        key="connected",
        name="Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda api: bool(api.data_moto.get("isConnected")),
    ),
    NiuBinarySensorEntityDescription(
        key="charging",
        name="Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda api: is_truthy_flag(api.data_moto.get("isCharging")),
    ),
    NiuBinarySensorEntityDescription(
        key="seat_lock",
        name="Seat Lock",
        value_fn=lambda api: bool(api.data_moto.get("is_cushion_lock_on")),
    ),
    NiuBinarySensorEntityDescription(
        key="battery_compartment_lock",
        name="Battery Compartment Lock",
        value_fn=lambda api: bool(api.data_moto.get("battery_cang_lock")),
    ),
    NiuBinarySensorEntityDescription(
        key="alarm_sound_enabled",
        name="Alarm Sound Enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda api: bool(api.data_moto.get("alarm_sound_status")),
    ),
    NiuBinarySensorEntityDescription(
        key="low_power_mode",
        name="Low Power Mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda api: api.data_moto.get("low_power_mode_value") not in (0, "0", None),
    ),
    NiuBinarySensorEntityDescription(
        key="tire_gauge_connected",
        name="Tire Gauge Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda api: bool(api.data_moto.get("is_tire_gauge_connected")),
    ),
    NiuBinarySensorEntityDescription(
        key="dash_cam_sentry_mode",
        name="Dash Cam Sentry Mode",
        value_fn=lambda api: is_truthy_flag(
            api.data_moto.get("dash_cam_status", {}).get("sentry_switch")
        ),
    ),
    NiuBinarySensorEntityDescription(
        key="dash_cam_abnormal",
        name="Dash Cam Abnormal",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda api: is_truthy_flag(api.data_moto.get("dash_cam_status", {}).get("abnormal")),
    ),
    *_wheel_binary_sensors("front", "Front"),
    *_wheel_binary_sensors("back", "Rear"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Niu binary sensors for one scooter."""
    coordinator: NiuDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    api = coordinator.api

    descriptions = list(BINARY_SENSORS)
    for compartment in api.battery_compartments():
        descriptions.extend(_battery_binary_sensors(compartment))

    async_add_entities(
        NiuBinarySensor(coordinator, description)
        for description in descriptions
        if description.exists_fn(api)
    )


class NiuBinarySensor(NiuEntity, BinarySensorEntity):
    """A single Niu binary sensor built from a NiuBinarySensorEntityDescription."""

    entity_description: NiuBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: NiuDataUpdateCoordinator,
        description: NiuBinarySensorEntityDescription,
    ) -> None:
        self.entity_description = description
        super().__init__(coordinator, description.key)

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.api)
