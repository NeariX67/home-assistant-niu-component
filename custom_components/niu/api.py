"""Thin client for the (unofficial) Niu cloud API."""
from __future__ import annotations

import hashlib
import json
import logging

import requests

from .const import (
    ACCOUNT_BASE_URL,
    ALIGN_API_URI,
    API_BASE_URL,
    BATTERY_COMPARTMENTS,
    CMD_ACC_OFF,
    CMD_ACC_ON,
    CMD_API_URI,
    CMD_FORTIFICATION_OFF,
    CMD_FORTIFICATION_ON,
    LOGIN_URI,
    MOTOINFO_ALL_API_URI,
    MOTOINFO_LIST_API_URI,
    MOTOR_BATTERY_API_URI,
    MOTOR_INDEX_API_URI,
    SOUND_API_URI,
    TRACK_LIST_API_URI,
)
from .util import as_int, is_truthy_flag

_LOGGER = logging.getLogger(__name__)


class NiuApiError(Exception):
    """Raised when the Niu cloud API can't be reached or returns junk."""


class NiuApi:
    """Client for a single scooter on a Niu account."""

    def __init__(self, username, password, scooter_id, language="en-US", timezone="UTC") -> None:
        self.username = username
        self.password = password
        self.scooter_id = int(scooter_id)
        self.language = language
        self.timezone = timezone

        self.token = None
        self.sn = None
        self.sensor_prefix = None

        self.dataBat = None
        self.dataMoto = None
        self.dataMotoInfo = None
        self.dataTrackInfo = None
        self.dataAlign = None
        self.dataSound = None

    @classmethod
    def from_hass(cls, hass, username, password, scooter_id):
        """Create NiuApi with locale settings from Home Assistant config."""
        language = hass.config.language
        # Only append country if language is a bare code (e.g. "en"),
        # not if it already includes a region (e.g. "en-GB", "zh-Hans")
        if hass.config.country and "-" not in language:
            language = f"{language}-{hass.config.country}"
        return cls(username, password, scooter_id, language=language, timezone=str(hass.config.time_zone))

    def initApi(self):
        """Log in, resolve the configured scooter's serial number, and fetch initial data."""
        self.token = self.get_token()
        if not self.token:
            raise NiuApiError("Login failed - check your Niu username and password")

        vehicles = self.get_vehicles_info(MOTOINFO_LIST_API_URI)
        if not vehicles:
            raise NiuApiError("Could not retrieve the list of vehicles on this Niu account")
        try:
            vehicle = vehicles["data"]["items"][self.scooter_id]
        except (KeyError, IndexError, TypeError) as err:
            raise NiuApiError(f"No vehicle at index {self.scooter_id} on this Niu account") from err

        self.sn = vehicle["sn_id"]
        self.sensor_prefix = vehicle["scooter_name"]
        self.update_all()

    def get_token(self):
        url = ACCOUNT_BASE_URL + LOGIN_URI
        md5 = hashlib.md5(self.password.encode("utf-8")).hexdigest()
        data = {
            "account": self.username,
            "password": md5,
            "grant_type": "password",
            "scope": "base",
            "app_id": "niu_ktdrr960",
        }
        try:
            r = requests.post(url, data=data)
        except requests.RequestException as err:
            _LOGGER.error("Error logging in to Niu: %s", err)
            return False
        data = json.loads(r.content.decode())
        try:
            return data["data"]["token"]["access_token"]
        except (KeyError, TypeError):
            return False

    def get_vehicles_info(self, path):
        url = API_BASE_URL + path
        headers = {"token": self.token}
        try:
            r = requests.get(url, headers=headers, data=[])
        except requests.RequestException:
            return False
        if r.status_code != 200:
            return False
        return json.loads(r.content.decode())

    def _headers(self):
        is_chinese = self.language.startswith("zh")
        client_id = "Domestic" if is_chinese else "Overseas"
        return {
            "token": self.token,
            "Accept-Language": self.language,
            "user-agent": f"manager/4.10.4 (android; IN2020 11);lang={self.language};clientIdentifier={client_id};timezone={self.timezone};model=IN2020;deviceName=IN2020;ostype=android",
        }

    def get_info(self, path):
        url = API_BASE_URL + path
        params = {"sn": self.sn}
        try:
            r = requests.get(url, headers=self._headers(), params=params)
        except requests.RequestException:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        if data["status"] != 0:
            return False
        return data

    def post_info(self, path):
        url = API_BASE_URL + path
        headers = {"token": self.token, "Accept-Language": self.language}
        try:
            r = requests.post(url, headers=headers, params={}, data={"sn": self.sn})
        except requests.RequestException:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        if data["status"] != 0:
            return False
        return data

    def post_info_track(self, path):
        is_chinese = self.language.startswith("zh")
        client_id = "Domestic" if is_chinese else "Overseas"
        headers = {
            "token": self.token,
            "Accept-Language": self.language,
            "User-Agent": f"manager/1.0.0 (identifier);clientIdentifier={client_id}",
        }
        url = API_BASE_URL + path
        try:
            r = requests.post(
                url,
                headers=headers,
                params={},
                json={"index": "0", "pagesize": 10, "sn": self.sn},
            )
        except requests.RequestException:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        if data["status"] != 0:
            return False
        return data

    def action(self, cmd):
        url = API_BASE_URL + CMD_API_URI
        data = {"token": self.token, "sn": self.sn, "type": cmd}
        try:
            r = requests.post(url, headers=self._headers(), data=data)
        except requests.RequestException:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        if data["status"] != 0:
            return False
        return data

    def wake_up(self):
        """Wake up / unlock the scooter's electronics remotely (Niu calls this "ACC")."""
        return self.action(CMD_ACC_ON)

    def sleep(self):
        """Power the scooter's electronics back down remotely."""
        return self.action(CMD_ACC_OFF)

    def lock(self):
        """Arm the scooter's anti-theft alarm (Niu calls this "fortification")."""
        return self.action(CMD_FORTIFICATION_ON)

    def unlock(self):
        """Disarm the scooter's anti-theft alarm (Niu calls this "fortification")."""
        return self.action(CMD_FORTIFICATION_OFF)

    def post_align(self, fields: dict):
        """POST a partial update to the vehicle-settings "align" endpoint (e.g. charging speed).

        This is the same endpoint the Niu app uses to both read and write dozens of
        vehicle settings. `db_cmd_type` is "1" here because, unlike the app, this
        integration never has a live Bluetooth connection to the scooter to relay
        the change through instead.
        """
        url = API_BASE_URL + ALIGN_API_URI
        data = {"sn": self.sn, "db_cmd_type": "1", **fields}
        try:
            r = requests.post(url, headers=self._headers(), json=data)
        except requests.RequestException:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        if data["status"] != 0:
            return False
        return data

    def set_charge_power(self, value: str):
        """Set the charging power. `value` must fall within `charge_power_range`."""
        return self.post_align({"charge_power_set_value": str(value)})

    def set_charging_limit(self, value: str):
        """Set the charging-limit percentage. `value` must be one of "80"/"85"/"90"/"95"/"100"."""
        return self.post_align({"charging_limit_value": str(value)})

    def post_sound(self, fields: dict):
        """POST a partial update to the vehicle sound/volume endpoint. See `post_align`."""
        url = API_BASE_URL + SOUND_API_URI
        data = {"sn": self.sn, "db_cmd_type": "1", **fields}
        try:
            r = requests.post(url, headers=self._headers(), json=data)
        except requests.RequestException:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        if data["status"] != 0:
            return False
        return data

    def set_volume(self, value: int):
        """Set the horn/alert volume level (0 to `sound_volume_max`)."""
        return self.post_sound({"cur_sound_volume": str(value)})

    # -- Parsed data access -------------------------------------------------

    @property
    def data_battery(self) -> dict:
        """Parsed data from the battery_info endpoint."""
        return (self.dataBat or {}).get("data") or {}

    @property
    def data_moto(self) -> dict:
        """Parsed data from the motor_data/index_info endpoint."""
        return (self.dataMoto or {}).get("data") or {}

    @property
    def data_overall(self) -> dict:
        """Parsed data from the overallTally endpoint."""
        return (self.dataMotoInfo or {}).get("data") or {}

    @property
    def data_last_track(self) -> dict:
        """The most recently completed trip from the track list endpoint, if any."""
        tracks = (self.dataTrackInfo or {}).get("data") or []
        return tracks[0] if tracks else {}

    @property
    def data_align(self) -> dict:
        """Parsed data from the car_machine/align endpoint (vehicle settings, incl. charging speed)."""
        return (self.dataAlign or {}).get("data") or {}

    @property
    def data_sound(self) -> dict:
        """Parsed data from the sound/theme endpoint (vehicle volume)."""
        return (self.dataSound or {}).get("data") or {}

    def battery_compartments(self) -> list[str]:
        """Return the letters (A/B/C) of the battery compartments this scooter reports."""
        batteries = self.data_battery.get("batteries") or {}
        return [c for c in BATTERY_COMPARTMENTS if f"compartment{c}" in batteries]

    def battery(self, compartment: str) -> dict:
        """Return the raw battery_info payload for one compartment (A/B/C)."""
        batteries = self.data_battery.get("batteries") or {}
        return batteries.get(f"compartment{compartment}") or {}

    def is_acc_on(self) -> bool:
        # Niu's API has been observed returning this as either a number or a numeric string.
        return self.data_moto.get("isAccOn") in (1, "1", True)

    def is_fortified(self) -> bool:
        return self.data_moto.get("isFortificationOn") in (1, "1", True)

    @property
    def charge_power_range(self) -> list[str]:
        """The [min, max] raw wattage range `set_charge_power` accepts, as strings.

        Empty if this scooter doesn't report a usable range.
        """
        charge_power = self.data_align.get("charge_power_set_value") or {}
        values = charge_power.get("charge_power_range") or []
        return values if len(values) == 2 else []

    @property
    def charge_power_current(self) -> str | None:
        """The raw current charging-power setting (what `set_charge_power` expects back)."""
        charge_power = self.data_align.get("charge_power_set_value") or {}
        return charge_power.get("set_value") or None

    def supports_charge_power(self) -> bool:
        """Whether this scooter supports setting a custom charging power at all."""
        return (
            is_truthy_flag(self.data_align.get("sup_charge_power_set"))
            and len(self.charge_power_range) == 2
        )

    @property
    def charging_limit_current(self) -> str | None:
        """The raw current charging-limit percentage (e.g. "100")."""
        return self.data_align.get("charging_limit_value") or None

    def supports_charging_limit(self) -> bool:
        """Whether this scooter supports capping its charge limit percentage."""
        return is_truthy_flag(self.data_align.get("sup_charging_limit"))

    @property
    def sound_volume_current(self) -> int | None:
        """The scooter's current horn/alert volume level."""
        return as_int(self.data_sound.get("cur_sound_volume"))

    @property
    def sound_volume_max(self) -> int | None:
        """The maximum horn/alert volume level this scooter supports (range is 0 to this)."""
        return as_int(self.data_sound.get("sup_sound_volume_max"))

    # -- Polling --------------------------------------------------------

    def updateBat(self):
        self.dataBat = self.get_info(MOTOR_BATTERY_API_URI)

    def updateMoto(self):
        self.dataMoto = self.get_info(MOTOR_INDEX_API_URI)

    def updateMotoInfo(self):
        self.dataMotoInfo = self.post_info(MOTOINFO_ALL_API_URI)

    def updateTrackInfo(self):
        self.dataTrackInfo = self.post_info_track(TRACK_LIST_API_URI)

    def updateAlign(self):
        self.dataAlign = self.get_info(ALIGN_API_URI)

    def updateSound(self):
        self.dataSound = self.get_info(SOUND_API_URI)

    def update_all(self):
        """Refresh every endpoint used by this integration in one pass."""
        self.updateBat()
        self.updateMoto()
        self.updateMotoInfo()
        self.updateTrackInfo()
        if not (self.dataBat and self.dataMoto and self.dataMotoInfo and self.dataTrackInfo):
            raise NiuApiError("Niu API returned an incomplete response")
        # Best-effort: not every scooter model exposes these endpoints, so a
        # failure here shouldn't take down the rest of the integration.
        self.updateAlign()
        self.updateSound()
