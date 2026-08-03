"""Remote anti-theft lock for Niu Integration integration."""
from datetime import timedelta
import logging

from homeassistant.components.lock import LockEntity
from homeassistant.util import Throttle

from .api import NiuApi
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    niu_auth = entry.data.get(CONF_AUTH, None)
    if niu_auth == None:
        _LOGGER.error(
            "The authenticator of your Niu integration is None.. can not setup the integration..."
        )
        return False

    username = niu_auth[CONF_USERNAME]
    password = niu_auth[CONF_PASSWORD]
    scooter_id = niu_auth[CONF_SCOOTER_ID]

    api = NiuApi.from_hass(hass, username, password, scooter_id)
    await hass.async_add_executor_job(api.initApi)

    async_add_entities([NiuFortificationLock(hass, api)])
    return True


class NiuFortificationLock(LockEntity):
    """Arms/disarms the scooter's anti-theft alarm (NIU calls this "fortification").

    This is a different concept from the `lockStatus` field the `IsLocked` sensor
    reports, which reflects the scooter's own electronic lock actuator rather than
    the remote anti-theft alarm system.
    """

    def __init__(self, hass, api: NiuApi) -> None:
        self._unique_id = "lock.niu_scooter_" + api.sn + "_fortification"
        self._name = "NIU Scooter " + api.sensor_prefix + " Lock"
        self._hass = hass
        self._api = api
        self._is_locked = api.is_fortified()

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return "mdi:lock" if self._is_locked else "mdi:lock-open"

    @property
    def is_locked(self):
        return self._is_locked

    @property
    def device_info(self):
        device_name = "Niu E-scooter"
        return {
            "identifiers": {("niu", device_name)},
            "name": device_name,
            "manufacturer": "Niu",
            "model": 1.0,
        }

    async def async_lock(self, **kwargs):
        await self._hass.async_add_executor_job(self._api.lock)
        self._is_locked = True
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs):
        await self._hass.async_add_executor_job(self._api.unlock)
        self._is_locked = False
        self.async_write_ha_state()

    @Throttle(timedelta(minutes=15))
    async def async_update(self):
        await self._hass.async_add_executor_job(self._api.updateMoto)
        self._is_locked = self._api.is_fortified()
