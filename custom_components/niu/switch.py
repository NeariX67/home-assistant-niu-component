"""Remote wake up / unlock switch for Niu Integration integration."""
from datetime import timedelta
import logging

from homeassistant.components.switch import SwitchEntity
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

    async_add_entities([NiuWakeSwitch(hass, api)])
    return True


class NiuWakeSwitch(SwitchEntity):
    """Remotely wakes up / unlocks the scooter (turn on) or powers it back down (turn off)."""

    def __init__(self, hass, api: NiuApi) -> None:
        self._unique_id = "switch.niu_scooter_" + api.sn + "_wake"
        self._name = "NIU Scooter " + api.sensor_prefix + " Wake"
        self._hass = hass
        self._api = api
        self._is_on = api.is_acc_on()

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return "mdi:motorbike-electric"

    @property
    def is_on(self):
        return self._is_on

    @property
    def device_info(self):
        device_name = "Niu E-scooter"
        return {
            "identifiers": {("niu", device_name)},
            "name": device_name,
            "manufacturer": "Niu",
            "model": 1.0,
        }

    async def async_turn_on(self, **kwargs):
        await self._hass.async_add_executor_job(self._api.wake_up)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._hass.async_add_executor_job(self._api.sleep)
        self._is_on = False
        self.async_write_ha_state()

    @Throttle(timedelta(minutes=15))
    async def async_update(self):
        await self._hass.async_add_executor_job(self._api.updateMoto)
        self._is_on = self._api.is_acc_on()
