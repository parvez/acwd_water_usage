import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN

class AcwdWaterUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ACWD Water Usage."""

    async def async_step_user(self, user_input=None):
        """Manage the configurations from the user interface."""
        errors = {}

        if user_input is not None:
            # Validate user input here and process the configuration
            return self.async_create_entry(title=self.hass.localize("config.title"), data=user_input)

        data_schema = vol.Schema({
            vol.Required("username", description={"suggested_value": self.hass.localize("config.step.user.data.username")}): str,
            vol.Required("password", description={"suggested_value": self.hass.localize("config.step.user.data.password")}): str,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={
                "description": self.hass.localize("config.step.user.description")
            }
        )


