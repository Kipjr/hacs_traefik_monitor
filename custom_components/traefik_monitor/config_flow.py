import voluptuous as vol
from homeassistant import config_entries
from .api import TraefikApiClient
from .const import *
from .exceptions import TraefikApiAuthError, TraefikApiConnectionError, TraefikApiError

class TraefikMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            client = TraefikApiClient(user_input[CONF_HOST].strip(), user_input[CONF_PORT], user_input[CONF_SSL], user_input[CONF_VERIFY_SSL], user_input.get(CONF_USERNAME), user_input.get(CONF_PASSWORD))
            try:
                await client.test()
            except TraefikApiAuthError: errors["base"]="invalid_auth"
            except TraefikApiConnectionError: errors["base"]="cannot_connect"
            except TraefikApiError: errors["base"]="invalid_response"
            finally: await client.close()
            if not errors:
                await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Traefik {user_input[CONF_HOST]}", data=user_input)
        schema = vol.Schema({vol.Required(CONF_HOST):str, vol.Required(CONF_PORT,default=DEFAULT_PORT):vol.All(vol.Coerce(int),vol.Range(min=1,max=65535)),vol.Required(CONF_SSL,default=False):bool,vol.Required(CONF_VERIFY_SSL,default=True):bool,vol.Optional(CONF_USERNAME):str,vol.Optional(CONF_PASSWORD):str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
