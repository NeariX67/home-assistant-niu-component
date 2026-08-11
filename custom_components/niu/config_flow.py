"""Config flow for the Niu integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import NiuApi
from .const import (
    CONF_AUTH,
    CONF_PASSWORD,
    CONF_SCOOTER_ID,
    CONF_USERNAME,
    DEFAULT_SCOOTER_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_SCOOTER_ID, default=DEFAULT_SCOOTER_ID): int,
    }
)


async def _authenticate(hass, username: str, password: str, scooter_id: int) -> bool:
    """Verify the given Niu credentials work."""
    api = NiuApi.from_hass(hass, username, password, scooter_id)
    try:
        token = await hass.async_add_executor_job(api.get_token)
    except Exception:  # noqa: BLE001 - any failure here just means "invalid"
        _LOGGER.exception("Unexpected error validating Niu credentials")
        return False
    return bool(token)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Niu Scooters."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Invoked when a user clicks the add button."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            scooter_id = user_input[CONF_SCOOTER_ID]

            if await _authenticate(self.hass, username, password, scooter_id):
                return self.async_create_entry(
                    title="Niu Scooters",
                    data={
                        CONF_AUTH: {
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_SCOOTER_ID: scooter_id,
                        }
                    },
                )
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
