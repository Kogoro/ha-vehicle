"""Base entities for the Vehicle integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ServiceItemData, VehicleCoordinator


class VehicleEntity(CoordinatorEntity[VehicleCoordinator]):
    """An entity belonging to the vehicle device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VehicleCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Vehicle",
            model=coordinator.fuel_type.value.capitalize(),
        )


class ServiceItemEntity(VehicleEntity):
    """An entity of a service item.

    Items share the vehicle's device, so the UI only ever shows one device per
    vehicle. Their entities are deliberately not attached to the config
    subentry: on current Home Assistant versions that would move the shared
    device onto the subentry.
    """

    def __init__(
        self, coordinator: VehicleCoordinator, subentry_id: str, key: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, f"{subentry_id}_{key}")
        self.subentry_id = subentry_id

    @property
    def item(self) -> ServiceItemData | None:
        """Return the computed data of this service item."""
        return self.coordinator.data.items.get(self.subentry_id)

    @property
    def available(self) -> bool:
        """The entity is available while the item exists."""
        return super().available and self.item is not None
