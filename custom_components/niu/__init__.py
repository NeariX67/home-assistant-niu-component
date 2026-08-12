"""The Niu integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import NiuApi, NiuApiError
from .const import CONF_AUTH, CONF_PASSWORD, CONF_SCOOTER_ID, CONF_USERNAME, DOMAIN
from .coordinator import NiuDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "device_tracker", "lock", "switch", "select", "camera"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Niu component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Niu scooter from a config entry."""
    niu_auth = entry.data.get(CONF_AUTH)
    if niu_auth is None:
        _LOGGER.error("Niu config entry %s has no stored credentials", entry.entry_id)
        return False

    api = NiuApi.from_hass(
        hass,
        niu_auth[CONF_USERNAME],
        niu_auth[CONF_PASSWORD],
        niu_auth[CONF_SCOOTER_ID],
    )

    try:
        await hass.async_add_executor_job(api.initApi)
    except NiuApiError as err:
        raise ConfigEntryNotReady(f"Unable to connect to Niu: {err}") from err

    coordinator = NiuDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
