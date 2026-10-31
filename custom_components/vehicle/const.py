"""Constants for the Vehicle integration."""

from enum import StrEnum

DOMAIN = "vehicle"
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION = 1

# Config entry data
CONF_FUEL_TYPE = "fuel_type"
CONF_ODOMETER_ENTITY = "odometer_entity"
CONF_WARN_DAYS = "warn_days"
CONF_WARN_KM = "warn_km"

# Service item (subentry) data
SUBENTRY_TYPE_SERVICE = "service_item"
CONF_INTERVAL_DAYS = "interval_days"
CONF_INTERVAL_KM = "interval_km"
CONF_LAST_DATE = "last_service_date"
CONF_LAST_ODOMETER = "last_service_odometer"
CONF_ICON = "icon"
CONF_DESCRIPTION = "description"

DEFAULT_WARN_DAYS = 30
DEFAULT_WARN_KM = 1000

# Service names
SERVICE_SET_ODOMETER = "set_odometer"
SERVICE_ADD_FUEL = "add_fuel"
SERVICE_ADD_CHARGE = "add_charge"
SERVICE_COMPLETE_SERVICE = "complete_service"

# Events
EVENT_SERVICE_OVERDUE = "vehicle_service_overdue"
EVENT_SERVICE_DUE_SOON = "vehicle_service_due_soon"
EVENT_SERVICE_COMPLETED = "vehicle_service_completed"

# unique-id suffixes of the vehicle-level entities (everything else belongs to a service item)
VEHICLE_KEYS = (
    "odometer",
    "fuel_consumption",
    "energy_consumption",
    "fuel_price",
    "energy_price",
    "cost_per_km",
    "monthly_cost",
    "monthly_service_cost",
)

# Number of log entries exposed as attribute
# Number of merged activity entries (fuel, charge, service) exposed as attribute
ACTIVITY_SIZE = 40


class FuelType(StrEnum):
    """Supported drive types."""

    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"

    @property
    def uses_fuel(self) -> bool:
        """Return True if the vehicle is refuelled with liquid fuel."""
        return self is not FuelType.ELECTRIC

    @property
    def uses_energy(self) -> bool:
        """Return True if the vehicle is charged with electricity."""
        return self in (FuelType.HYBRID, FuelType.ELECTRIC)


class ServiceStatus(StrEnum):
    """Status of a service item."""

    OK = "ok"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"
    UNKNOWN = "unknown"
