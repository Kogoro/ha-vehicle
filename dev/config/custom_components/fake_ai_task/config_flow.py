"""Config flow for the dev-only fake AI task provider."""

from homeassistant.config_entries import ConfigFlow


class FakeAiTaskFlow(ConfigFlow, domain="fake_ai_task"):
    """Single-step flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create the entry."""
        await self.async_set_unique_id("fake_ai_task")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Fake AI Task (dev only)", data={})
