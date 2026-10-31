"""The Vehicle integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .calc import KIND_CHARGE, KIND_FUEL
from .const import (
    DOMAIN,
    SERVICE_ADD_CHARGE,
    SERVICE_ADD_FUEL,
    SERVICE_COMPLETE_SERVICE,
    SERVICE_SET_ODOMETER,
    SUBENTRY_TYPE_SERVICE,
)
from .coordinator import VehicleConfigEntry, VehicleCoordinator
from .store import VehicleStore

_LOGGER = logging.getLogger(__name__)

FRONTEND_SCRIPT_PATH = f"/{DOMAIN}/vehicle-card.js"
FRONTEND_SCRIPT_URL = f"{FRONTEND_SCRIPT_PATH}?v=0.1.0"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

_ENTITY = {vol.Required("entity_id"): cv.entity_id}
_OPT_DATE = {vol.Optional("date"): cv.date}
_ODOMETER = vol.All(vol.Coerce(float), vol.Range(min=0))
_POSITIVE = vol.All(vol.Coerce(float), vol.Range(min=0, min_included=False))
_COST = vol.All(vol.Coerce(float), vol.Range(min=0))

SET_ODOMETER_SCHEMA = vol.Schema(
    {
        **_ENTITY,
        vol.Required("odometer"): _ODOMETER,
        vol.Optional("allow_decrease", default=False): cv.boolean,
    }
)
ADD_FUEL_SCHEMA = vol.Schema(
    {
        **_ENTITY,
        **_OPT_DATE,
        vol.Required("liters"): _POSITIVE,
        vol.Optional("total_cost"): _COST,
        vol.Optional("price_per_liter"): _COST,
        vol.Optional("odometer"): _ODOMETER,
    }
)
ADD_CHARGE_SCHEMA = vol.Schema(
    {
        **_ENTITY,
        **_OPT_DATE,
        vol.Required("kwh"): _POSITIVE,
        vol.Optional("total_cost"): _COST,
        vol.Optional("price_per_kwh"): _COST,
        vol.Optional("odometer"): _ODOMETER,
    }
)
COMPLETE_SERVICE_SCHEMA = vol.Schema(
    {**_ENTITY, **_OPT_DATE, vol.Optional("odometer"): _ODOMETER}
)


def _resolve(
    hass: HomeAssistant, entity_id: str
) -> tuple[VehicleCoordinator, er.RegistryEntry]:
    """Find the coordinator that owns an entity of this integration."""
    entity = er.async_get(hass).async_get(entity_id)
    if entity is None or entity.platform != DOMAIN or not entity.config_entry_id:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_vehicle_entity",
            translation_placeholders={"entity_id": entity_id},
        )
    entry = hass.config_entries.async_get_entry(entity.config_entry_id)
    if entry is None or not isinstance(
        getattr(entry, "runtime_data", None), VehicleCoordinator
    ):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="vehicle_not_loaded",
            translation_placeholders={"entity_id": entity_id},
        )
    return entry.runtime_data, entity


def _price_and_cost(
    total: float | None, unit_price: float | None, amount: float
) -> tuple[float, float]:
    """Return (unit price, total cost); the unit price is the primary input.

    If only a total is given the unit price is derived from it, so every
    entry carries a price that can be trended.
    """
    if unit_price is not None:
        return round(unit_price, 4), round(total if total is not None else unit_price * amount, 2)
    if total is not None:
        return round(total / amount, 4), round(total, 2)
    raise ServiceValidationError(
        translation_domain=DOMAIN, translation_key="price_required"
    )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up services, storage and the Lovelace card."""
    store = VehicleStore(hass)
    await store.async_load()
    hass.data[DOMAIN] = {"store": store}

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=FRONTEND_SCRIPT_PATH,
                path=str(Path(__file__).parent / "www" / "vehicle-card.js"),
                cache_headers=False,
            )
        ]
    )
    add_extra_js_url(hass, FRONTEND_SCRIPT_URL)

    async def set_odometer(call: ServiceCall) -> None:
        coordinator, _ = _resolve(hass, call.data["entity_id"])
        if not store.set_odometer(
            coordinator.config_entry.entry_id,
            call.data["odometer"],
            allow_decrease=call.data["allow_decrease"],
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="odometer_decrease"
            )
        await coordinator.async_refresh()

    async def add_fuel(call: ServiceCall) -> None:
        coordinator, _ = _resolve(hass, call.data["entity_id"])
        if not coordinator.fuel_type.uses_fuel:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="no_fuel_vehicle"
            )
        liters = call.data["liters"]
        price, cost = _price_and_cost(
            call.data.get("total_cost"), call.data.get("price_per_liter"), liters
        )
        store.add_log(
            coordinator.config_entry.entry_id,
            {
                "kind": KIND_FUEL,
                "date": (call.data.get("date") or dt_util.now().date()).isoformat(),
                "amount": liters,
                "price": price,
                "cost": cost,
                "odometer": call.data.get("odometer"),
            },
        )
        await coordinator.async_refresh()

    async def add_charge(call: ServiceCall) -> None:
        coordinator, _ = _resolve(hass, call.data["entity_id"])
        if not coordinator.fuel_type.uses_energy:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="no_electric_vehicle"
            )
        kwh = call.data["kwh"]
        price, cost = _price_and_cost(
            call.data.get("total_cost"), call.data.get("price_per_kwh"), kwh
        )
        store.add_log(
            coordinator.config_entry.entry_id,
            {
                "kind": KIND_CHARGE,
                "date": (call.data.get("date") or dt_util.now().date()).isoformat(),
                "amount": kwh,
                "price": price,
                "cost": cost,
                "odometer": call.data.get("odometer"),
            },
        )
        await coordinator.async_refresh()

    async def complete_service(call: ServiceCall) -> None:
        coordinator, entity = _resolve(hass, call.data["entity_id"])
        if not entity.config_subentry_id:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_service_entity",
                translation_placeholders={"entity_id": call.data["entity_id"]},
            )
        await coordinator.async_complete_service(
            entity.config_subentry_id,
            date=call.data.get("date"),
            odometer=call.data.get("odometer"),
        )

    for name, handler, schema in (
        (SERVICE_SET_ODOMETER, set_odometer, SET_ODOMETER_SCHEMA),
        (SERVICE_ADD_FUEL, add_fuel, ADD_FUEL_SCHEMA),
        (SERVICE_ADD_CHARGE, add_charge, ADD_CHARGE_SCHEMA),
        (SERVICE_COMPLETE_SERVICE, complete_service, COMPLETE_SERVICE_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=schema)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: VehicleConfigEntry) -> bool:
    """Set up a vehicle from a config entry."""
    store: VehicleStore = hass.data[DOMAIN]["store"]
    coordinator = VehicleCoordinator(hass, entry, store)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    coordinator.start_tracking()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    return True


async def _async_entry_updated(hass: HomeAssistant, entry: VehicleConfigEntry) -> None:
    """Reload on config or subentry changes and drop history of deleted items."""
    store: VehicleStore = hass.data[DOMAIN]["store"]
    known = {
        sid
        for entries in hass.config_entries.async_entries(DOMAIN)
        for sid, sub in entries.subentries.items()
        if sub.subentry_type == SUBENTRY_TYPE_SERVICE
    }
    store.prune_services(known)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: VehicleConfigEntry) -> bool:
    """Unload a vehicle."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: VehicleConfigEntry) -> None:
    """Delete stored data of a removed vehicle."""
    store: VehicleStore = hass.data[DOMAIN]["store"]
    for sid in entry.subentries:
        store.remove_service(sid)
    store.remove_vehicle(entry.entry_id)
