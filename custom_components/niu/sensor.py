"""Sensor platform for the Niu integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import NiuApi
from .const import DOMAIN
from .coordinator import NiuDataUpdateCoordinator
from .entity import NiuEntity
from .util import as_float, as_int, epoch_ms_to_datetime


@dataclass(frozen=True, kw_only=True)
class NiuSensorEntityDescription(SensorEntityDescription):
    """Describes a Niu sensor sourced from one field of the Niu cloud API."""

    value_fn: Callable[[NiuApi], StateType | datetime]
    exists_fn: Callable[[NiuApi], bool] = lambda api: True


def _charging_time_left(api: NiuApi) -> float | None:
    hours = as_float(api.data_moto.get("leftTime"))
    if hours is None:
        return None
    if hours > 100:
        # The API reports a bogus, very large value right after the scooter is plugged in.
        return None
    return hours


def _charge_power_range(api: NiuApi, index: int) -> str | None:
    values = api.charge_power_range
    return values[index] if values else None


def _battery_sensors(compartment: str) -> list[NiuSensorEntityDescription]:
    """Build the sensor descriptions for one battery compartment (A/B/C)."""
    letter = compartment.lower()
    return [
        NiuSensorEntityDescription(
            key=f"battery_{letter}_charge",
            name=f"Battery {compartment} Charge",
            device_class=SensorDeviceClass.BATTERY,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda api, c=compartment: api.battery(c).get("batteryCharging"),
        ),
        NiuSensorEntityDescription(
            key=f"battery_{letter}_health",
            name=f"Battery {compartment} Health",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:heart-pulse",
            value_fn=lambda api, c=compartment: as_float(api.battery(c).get("gradeBattery")),
        ),
        NiuSensorEntityDescription(
            key=f"battery_{letter}_temperature",
            name=f"Battery {compartment} Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda api, c=compartment: api.battery(c).get("temperature"),
        ),
        NiuSensorEntityDescription(
            key=f"battery_{letter}_temperature_description",
            name=f"Battery {compartment} Temperature Description",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:thermometer-alert",
            value_fn=lambda api, c=compartment: api.battery(c).get("temperatureDesc"),
        ),
        NiuSensorEntityDescription(
            key=f"battery_{letter}_charge_cycles",
            name=f"Battery {compartment} Charge Cycles",
            state_class=SensorStateClass.TOTAL_INCREASING,
            icon="mdi:battery-sync",
            value_fn=lambda api, c=compartment: as_int(api.battery(c).get("chargedTimes")),
        ),
        NiuSensorEntityDescription(
            key=f"battery_{letter}_used_today",
            name=f"Battery {compartment} Used Today",
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:battery-arrow-down",
            value_fn=lambda api, c=compartment: api.battery(c).get("energyConsumedTody"),
        ),
        NiuSensorEntityDescription(
            key=f"battery_{letter}_bms_id",
            name=f"Battery {compartment} BMS ID",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            icon="mdi:identifier",
            value_fn=lambda api, c=compartment: api.battery(c).get("bmsId"),
        ),
    ]


def _wheel_sensors(wheel: str, label: str) -> list[NiuSensorEntityDescription]:
    """Build sensors for a TPMS wheel sensor. Only created if it's actually paired."""

    def paired(api: NiuApi, w=wheel) -> bool:
        return bool(api.data_moto.get(f"{w}_wheel_status", {}).get("paired"))

    return [
        NiuSensorEntityDescription(
            key=f"{wheel}_wheel_pressure",
            name=f"{label} Wheel Pressure",
            device_class=SensorDeviceClass.PRESSURE,
            native_unit_of_measurement=UnitOfPressure.KPA,
            state_class=SensorStateClass.MEASUREMENT,
            exists_fn=paired,
            value_fn=lambda api, w=wheel: api.data_moto.get(f"{w}_wheel_pressure"),
        ),
        NiuSensorEntityDescription(
            key=f"{wheel}_wheel_id",
            name=f"{label} Wheel Sensor ID",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            icon="mdi:identifier",
            exists_fn=paired,
            value_fn=lambda api, w=wheel: api.data_moto.get(f"{w}_wheel_id"),
        ),
    ]


SENSORS: tuple[NiuSensorEntityDescription, ...] = (
    NiuSensorEntityDescription(
        key="speed",
        name="Speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda api: api.data_moto.get("nowSpeed"),
    ),
    NiuSensorEntityDescription(
        key="estimated_range",
        name="Estimated Range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda api: api.data_moto.get("estimatedMileage"),
    ),
    NiuSensorEntityDescription(
        key="charging_time_left",
        name="Charging Time Left",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=_charging_time_left,
    ),
    NiuSensorEntityDescription(
        key="charging_elapsed_time",
        name="Charging Elapsed Time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda api: as_float(api.data_moto.get("charging_time")),
    ),
    NiuSensorEntityDescription(
        key="charge_power_range_min",
        name="Charging Power Range Min (raw)",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:flash",
        exists_fn=lambda api: api.supports_charge_power(),
        value_fn=lambda api: _charge_power_range(api, 0),
    ),
    NiuSensorEntityDescription(
        key="charge_power_range_max",
        name="Charging Power Range Max (raw)",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:flash",
        exists_fn=lambda api: api.supports_charge_power(),
        value_fn=lambda api: _charge_power_range(api, 1),
    ),
    NiuSensorEntityDescription(
        key="central_control_battery",
        name="Central Control Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda api: as_float(api.data_moto.get("centreCtrlBattery")),
    ),
    NiuSensorEntityDescription(
        key="lock_status",
        name="Lock Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:lock-question",
        value_fn=lambda api: api.data_moto.get("lockStatus"),
    ),
    NiuSensorEntityDescription(
        key="riding_mode",
        name="Riding Mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:speedometer",
        value_fn=lambda api: api.data_moto.get("cycling_model"),
    ),
    NiuSensorEntityDescription(
        key="gps_hdop",
        name="GPS HDOP",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:crosshairs-gps",
        value_fn=lambda api: api.data_moto.get("hdop"),
    ),
    NiuSensorEntityDescription(
        key="gps_signal",
        name="GPS Signal",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:crosshairs-gps",
        value_fn=lambda api: api.data_moto.get("gps"),
    ),
    NiuSensorEntityDescription(
        key="gsm_signal",
        name="GSM Signal",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal",
        value_fn=lambda api: api.data_moto.get("gsm"),
    ),
    NiuSensorEntityDescription(
        key="shaking_value",
        name="Shaking Value",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:vibrate",
        value_fn=lambda api: api.data_moto.get("shakingValue"),
    ),
    NiuSensorEntityDescription(
        key="gps_timestamp",
        name="GPS Last Update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda api: epoch_ms_to_datetime(api.data_moto.get("gpsTimestamp")),
    ),
    NiuSensorEntityDescription(
        key="info_timestamp",
        name="Info Last Update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda api: epoch_ms_to_datetime(api.data_moto.get("infoTimestamp")),
    ),
    NiuSensorEntityDescription(
        key="estimated_mileage_ratio",
        name="Estimated Mileage Ratio (raw)",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:map-marker-distance",
        value_fn=lambda api: api.data_moto.get("estimatedMileageRatio"),
    ),
    NiuSensorEntityDescription(
        key="new_estimated_mileage_ratio",
        name="New Estimated Mileage Ratio (raw)",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:map-marker-distance",
        value_fn=lambda api: api.data_moto.get("newEstimatedMileageRatio"),
    ),
    NiuSensorEntityDescription(
        key="current_trip_distance",
        name="Current Trip Distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda api: api.data_moto.get("lastTrack", {}).get("distance"),
    ),
    NiuSensorEntityDescription(
        key="current_trip_riding_time",
        name="Current Trip Riding Time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda api: api.data_moto.get("lastTrack", {}).get("ridingTime"),
    ),
    NiuSensorEntityDescription(
        key="front_tire_gauge",
        name="Front Tire Gauge Reading",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        exists_fn=lambda api: bool(api.data_moto.get("is_tire_gauge_connected")),
        value_fn=lambda api: api.data_moto.get("frontend_tire_gauge_value"),
    ),
    NiuSensorEntityDescription(
        key="rear_tire_gauge",
        name="Rear Tire Gauge Reading",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        exists_fn=lambda api: bool(api.data_moto.get("is_tire_gauge_connected")),
        value_fn=lambda api: api.data_moto.get("backend_tire_gauge_value"),
    ),
    NiuSensorEntityDescription(
        key="total_mileage",
        name="Total Mileage",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda api: api.data_overall.get("totalMileage"),
    ),
    NiuSensorEntityDescription(
        key="days_in_use",
        name="Days In Use",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:calendar-today",
        value_fn=lambda api: api.data_overall.get("bindDaysCount"),
    ),
    NiuSensorEntityDescription(
        key="last_trip_start_time",
        name="Last Trip Start Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda api: epoch_ms_to_datetime(api.data_last_track.get("startTime")),
    ),
    NiuSensorEntityDescription(
        key="last_trip_end_time",
        name="Last Trip End Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda api: epoch_ms_to_datetime(api.data_last_track.get("endTime")),
    ),
    NiuSensorEntityDescription(
        key="last_trip_distance",
        name="Last Trip Distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        value_fn=lambda api: api.data_last_track.get("distance"),
    ),
    NiuSensorEntityDescription(
        key="last_trip_average_speed",
        name="Last Trip Average Speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        value_fn=lambda api: api.data_last_track.get("avespeed"),
    ),
    NiuSensorEntityDescription(
        key="last_trip_riding_time",
        name="Last Trip Riding Time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda api: api.data_last_track.get("ridingtime"),
    ),
    NiuSensorEntityDescription(
        key="last_trip_battery_used",
        name="Last Trip Battery Used",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery-arrow-down",
        value_fn=lambda api: api.data_last_track.get("power_consumption"),
    ),
    NiuSensorEntityDescription(
        key="riders_met",
        name="Riders Met",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:account-group",
        value_fn=lambda api: api.data_last_track.get("meet_count"),
    ),
    *_wheel_sensors("front", "Front"),
    *_wheel_sensors("back", "Rear"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Niu sensors for one scooter."""
    coordinator: NiuDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    api = coordinator.api

    descriptions = list(SENSORS)
    for compartment in api.battery_compartments():
        descriptions.extend(_battery_sensors(compartment))

    async_add_entities(
        NiuSensor(coordinator, description)
        for description in descriptions
        if description.exists_fn(api)
    )


class NiuSensor(NiuEntity, SensorEntity):
    """A single Niu sensor built from a NiuSensorEntityDescription."""

    entity_description: NiuSensorEntityDescription

    def __init__(
        self, coordinator: NiuDataUpdateCoordinator, description: NiuSensorEntityDescription
    ) -> None:
        self.entity_description = description
        super().__init__(coordinator, description.key)

    @property
    def native_value(self) -> StateType | datetime:
        return self.entity_description.value_fn(self.api)
