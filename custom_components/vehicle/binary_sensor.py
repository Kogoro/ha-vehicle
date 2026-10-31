"""Binary sensors for the Vehicle integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SUBENTRY_TYPE_SERVICE, ServiceStatus
from .coordinator import VehicleConfigEntry, VehicleCoordinator
from .entity import ServiceItemEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VehicleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up an overdue binary sensor for every service item."""
    for subentry in entry.subentries.values():
        if subentry.subentry_type == SUBENTRY_TYPE_SERVICE:
            async_add_entities(
                [ServiceOverdueSensor(entry.runtime_data, subentry.subentry_id)],
                config_subentry_id=subentry.subentry_id,
            )


class ServiceOverdueSensor(ServiceItemEntity, BinarySensorEntity):
    """On when a service item is overdue."""

    _attr_translation_key = "service_overdue"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: VehicleCoordinator, subentry_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, subentry_id, "overdue")

    @property
    def name(self) -> str | None:
        """Combine item name and measure."""
        return f"{self.item.name} overdue" if self.item else None

    @property
    def is_on(self) -> bool | None:
        """Return True if overdue."""
        return self.item.info.status is ServiceStatus.OVERDUE if self.item else None
