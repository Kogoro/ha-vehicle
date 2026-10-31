"""Buttons for the Vehicle integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SUBENTRY_TYPE_SERVICE
from .coordinator import VehicleConfigEntry, VehicleCoordinator
from .entity import ServiceItemEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VehicleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a complete button for every service item."""
    for subentry in entry.subentries.values():
        if subentry.subentry_type == SUBENTRY_TYPE_SERVICE:
            async_add_entities(
                [ServiceCompleteButton(entry.runtime_data, subentry.subentry_id)],
                config_subentry_id=subentry.subentry_id,
            )


class ServiceCompleteButton(ServiceItemEntity, ButtonEntity):
    """Records a service as done today at the current odometer."""

    _attr_translation_key = "service_complete"

    def __init__(self, coordinator: VehicleCoordinator, subentry_id: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, subentry_id, "complete")

    @property
    def name(self) -> str | None:
        """Combine item name and action."""
        return f"{self.item.name} complete" if self.item else None

    async def async_press(self) -> None:
        """Record the completion."""
        await self.coordinator.async_complete_service(self.subentry_id)
