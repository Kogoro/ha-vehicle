"""Sensors for the Vehicle integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SUBENTRY_TYPE_SERVICE, ServiceStatus
from .coordinator import VehicleConfigEntry, VehicleCoordinator, VehicleData
from .entity import ServiceItemEntity, VehicleEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class VehicleSensorDescription(SensorEntityDescription):
    """Describes a vehicle-level sensor."""

    value_fn: Callable[[VehicleData], float | None]
    attrs_fn: Callable[[VehicleData], dict[str, Any]] | None = None
    applies_fn: Callable[[VehicleCoordinator], bool] = lambda _: True


VEHICLE_SENSORS: tuple[VehicleSensorDescription, ...] = (
    VehicleSensorDescription(
        key="odometer",
        translation_key="odometer",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda d: d.odometer,
        attrs_fn=lambda d: {
            "source": d.odometer_source,
            "fuel_type": d.fuel_type.value,
            "recent_log": d.recent_log,
        },
    ),
    VehicleSensorDescription(
        key="fuel_consumption",
        translation_key="fuel_consumption",
        native_unit_of_measurement="L/100 km",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.fuel_consumption,
        attrs_fn=lambda d: {"recent": d.fuel_consumption_latest},
        applies_fn=lambda c: c.fuel_type.uses_fuel,
    ),
    VehicleSensorDescription(
        key="energy_consumption",
        translation_key="energy_consumption",
        native_unit_of_measurement="kWh/100 km",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.energy_consumption,
        attrs_fn=lambda d: {"recent": d.energy_consumption_latest},
        applies_fn=lambda c: c.fuel_type.uses_energy,
    ),
    VehicleSensorDescription(
        key="fuel_price",
        translation_key="fuel_price",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: d.fuel_price,
        applies_fn=lambda c: c.fuel_type.uses_fuel,
    ),
    VehicleSensorDescription(
        key="energy_price",
        translation_key="energy_price",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: d.energy_price,
        applies_fn=lambda c: c.fuel_type.uses_energy,
    ),
    VehicleSensorDescription(
        key="cost_per_km",
        translation_key="cost_per_km",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda d: d.cost_per_km,
    ),
    VehicleSensorDescription(
        key="monthly_cost",
        translation_key="monthly_cost",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value_fn=lambda d: d.monthly_cost,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VehicleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the vehicle sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        VehicleSensor(coordinator, description, hass.config.currency)
        for description in VEHICLE_SENSORS
        if description.applies_fn(coordinator)
    )
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_SERVICE:
            continue
        item = coordinator.data.items[subentry.subentry_id]
        entities: list[SensorEntity] = [
            ServiceStatusSensor(coordinator, subentry.subentry_id)
        ]
        if item.interval_days:
            entities.append(ServiceDaysSensor(coordinator, subentry.subentry_id))
        if item.interval_km:
            entities.append(ServiceKmSensor(coordinator, subentry.subentry_id))
        async_add_entities(entities, config_subentry_id=subentry.subentry_id)


class VehicleSensor(VehicleEntity, SensorEntity):
    """A vehicle-level sensor."""

    entity_description: VehicleSensorDescription

    def __init__(
        self,
        coordinator: VehicleCoordinator,
        description: VehicleSensorDescription,
        currency: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        if description.key == "monthly_cost":
            self._attr_native_unit_of_measurement = currency
        elif description.key == "fuel_price":
            self._attr_native_unit_of_measurement = f"{currency}/L"
        elif description.key == "energy_price":
            self._attr_native_unit_of_measurement = f"{currency}/kWh"
        elif description.key == "cost_per_km":
            self._attr_native_unit_of_measurement = f"{currency}/km"

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)


class ServiceStatusSensor(ServiceItemEntity, SensorEntity):
    """Status of a service item: ok, due soon, overdue or unknown."""

    _attr_translation_key = "service_status"
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: VehicleCoordinator, subentry_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, subentry_id, "status")
        self._attr_options = [status.value for status in ServiceStatus]

    @property
    def name(self) -> str | None:
        """Use the service item name."""
        return self.item.name if self.item else None

    @property
    def icon(self) -> str | None:
        """Use the configured icon, else the default for the status."""
        return self.item.icon if self.item and self.item.icon else None

    @property
    def native_value(self) -> str | None:
        """Return the status."""
        return self.item.info.status.value if self.item else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return all details of the item."""
        item = self.item
        if item is None:
            return None
        info = item.info
        return {
            "description": item.description,
            "interval_days": item.interval_days,
            "interval_km": item.interval_km,
            "last_date": item.last_date.isoformat() if item.last_date else None,
            "last_odometer": item.last_odometer,
            "next_due_date": info.next_due_date.isoformat() if info.next_due_date else None,
            "next_due_odometer": info.next_due_odometer,
            "days_remaining": info.days_remaining,
            "km_remaining": info.km_remaining,
            "history": item.history,
        }


class ServiceDaysSensor(ServiceItemEntity, SensorEntity):
    """Days until a service item is due (negative when overdue)."""

    _attr_translation_key = "service_days_remaining"
    _attr_native_unit_of_measurement = "d"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: VehicleCoordinator, subentry_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, subentry_id, "days_remaining")

    @property
    def name(self) -> str | None:
        """Combine item name and measure."""
        return f"{self.item.name} days remaining" if self.item else None

    @property
    def native_value(self) -> int | None:
        """Return the days remaining."""
        return self.item.info.days_remaining if self.item else None


class ServiceKmSensor(ServiceItemEntity, SensorEntity):
    """Kilometres until a service item is due (negative when overdue)."""

    _attr_translation_key = "service_km_remaining"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: VehicleCoordinator, subentry_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, subentry_id, "km_remaining")

    @property
    def name(self) -> str | None:
        """Combine item name and measure."""
        return f"{self.item.name} km remaining" if self.item else None

    @property
    def native_value(self) -> float | None:
        """Return the kilometres remaining."""
        return self.item.info.km_remaining if self.item else None
