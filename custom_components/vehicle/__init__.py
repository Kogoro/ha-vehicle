"""The Vehicle integration."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
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
from .receipts import (
    RECEIPT_RE,
    ReceiptView,
    async_cleanup_orphans,
    async_delete,
    async_import_upload,
    mime_type,
    receipt_path,
)
from .store import VehicleStore

_LOGGER = logging.getLogger(__name__)

FRONTEND_SCRIPT_PATH = f"/{DOMAIN}/vehicle-card.js"
FRONTEND_SCRIPT_URL = f"{FRONTEND_SCRIPT_PATH}?v=0.3.0"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

_ENTITY = {vol.Required("entity_id"): cv.entity_id}
_OPT_DATE = {vol.Optional("date"): cv.date}
_ODOMETER = vol.All(vol.Coerce(float), vol.Range(min=0))
_POSITIVE = vol.All(vol.Coerce(float), vol.Range(min=0, min_included=False))
_COST = vol.All(vol.Coerce(float), vol.Range(min=0))

_RECEIPT = {vol.Optional("receipt"): vol.All(cv.string, vol.Match(RECEIPT_RE))}

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
        **_RECEIPT,
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
        **_RECEIPT,
        vol.Required("kwh"): _POSITIVE,
        vol.Optional("total_cost"): _COST,
        vol.Optional("price_per_kwh"): _COST,
        vol.Optional("odometer"): _ODOMETER,
    }
)
COMPLETE_SERVICE_SCHEMA = vol.Schema(
    {
        **_ENTITY,
        **_OPT_DATE,
        **_RECEIPT,
        vol.Optional("odometer"): _ODOMETER,
        vol.Optional("cost"): _COST,
    }
)
UPLOAD_RECEIPT_SCHEMA = vol.Schema({vol.Required("file"): cv.string})
SCAN_RECEIPT_SCHEMA = vol.Schema(
    {
        vol.Required("receipt"): vol.All(cv.string, vol.Match(RECEIPT_RE)),
        vol.Required("kind"): vol.In(["fuel", "charge", "service"]),
        vol.Optional("ai_task_entity_id"): cv.entity_id,
    }
)
ATTACH_RECEIPT_SCHEMA = vol.Schema(
    {
        **_ENTITY,
        vol.Required("receipt"): vol.All(cv.string, vol.Match(RECEIPT_RE)),
        vol.Optional("log_entry_id"): cv.string,
    }
)
DELETE_LOG_ENTRY_SCHEMA = vol.Schema({**_ENTITY, vol.Required("log_entry_id"): cv.string})

# What the AI task should extract from a receipt or invoice.
_DATE = {"description": "Date of the receipt", "selector": {"date": {}}}
_NUMBER = {"mode": "box", "step": "any"}


def _number(description: str) -> dict[str, Any]:
    return {"description": description, "selector": {"number": _NUMBER}}


SCAN_STRUCTURES: dict[str, dict[str, Any]] = {
    "fuel": {
        "date": _DATE,
        "liters": _number("Amount of fuel in liters"),
        "price_per_liter": _number("Price per liter"),
        "total_cost": _number("Total amount paid"),
        "odometer": _number("Odometer reading in km, only if printed"),
    },
    "charge": {
        "date": _DATE,
        "kwh": _number("Energy charged in kWh"),
        "price_per_kwh": _number("Price per kWh"),
        "total_cost": _number("Total amount paid"),
        "odometer": _number("Odometer reading in km, only if printed"),
    },
    "service": {
        "date": _DATE,
        "odometer": _number("Odometer / mileage reading in km, only if printed"),
        "cost": _number("Total invoice amount including tax"),
    },
}
SCAN_INSTRUCTIONS = {
    "fuel": "This is a fuel station receipt. Extract the listed fields.",
    "charge": "This is an electric vehicle charging receipt. Extract the listed fields.",
    "service": "This is a vehicle workshop invoice. Extract the listed fields.",
}


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


def _clean_scan(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    """Keep only valid, non-empty values returned by the AI task."""
    values: dict[str, Any] = {}
    for key, raw in data.items():
        if key not in SCAN_STRUCTURES[kind] or raw in (None, "", 0):
            continue
        if key == "date":
            try:
                values[key] = datetime.date.fromisoformat(str(raw)[:10]).isoformat()
            except ValueError:
                continue
        else:
            try:
                number = float(raw)
            except (TypeError, ValueError):
                continue
            if number > 0:
                values[key] = round(number, 4)
    return values


async def _checked_receipt(hass: HomeAssistant, receipt: str | None) -> str | None:
    """Return the receipt id if it exists, else raise."""
    if receipt is None:
        return None
    if await hass.async_add_executor_job(receipt_path, hass, receipt) is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="receipt_not_found",
            translation_placeholders={"receipt": receipt},
        )
    return receipt


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
        receipt = await _checked_receipt(hass, call.data.get("receipt"))
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
                **({"receipt": receipt} if receipt else {}),
            },
        )
        await coordinator.async_refresh()

    async def add_charge(call: ServiceCall) -> None:
        coordinator, _ = _resolve(hass, call.data["entity_id"])
        if not coordinator.fuel_type.uses_energy:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="no_electric_vehicle"
            )
        receipt = await _checked_receipt(hass, call.data.get("receipt"))
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
                **({"receipt": receipt} if receipt else {}),
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
            cost=call.data.get("cost"),
            receipt=await _checked_receipt(hass, call.data.get("receipt")),
        )

    async def upload_receipt(call: ServiceCall) -> ServiceResponse:
        try:
            receipt_id = await async_import_upload(hass, call.data["file"])
        except HomeAssistantError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key=str(err)
            ) from err
        return {"receipt": receipt_id}

    async def scan_receipt(call: ServiceCall) -> ServiceResponse:
        receipt = await _checked_receipt(hass, call.data["receipt"])
        kind = call.data["kind"]
        if not hass.services.has_service("ai_task", "generate_data"):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="ai_task_unavailable"
            )
        request: dict[str, Any] = {
            "task_name": "Vehicle receipt",
            "instructions": (
                f"{SCAN_INSTRUCTIONS[kind]} Only fill in values that are clearly "
                "readable; leave everything else out. Do not guess."
            ),
            "structure": SCAN_STRUCTURES[kind],
            "attachments": [
                {
                    "media_content_id": f"media-source://{DOMAIN}/{receipt}",
                    "media_content_type": mime_type(receipt),
                }
            ],
        }
        if call.data.get("ai_task_entity_id"):
            request["entity_id"] = call.data["ai_task_entity_id"]
        elif len(candidates := hass.states.async_entity_ids("ai_task")) == 1:
            # a single provider needs no "preferred entity" to be configured
            request["entity_id"] = candidates[0]
        try:
            result = await hass.services.async_call(
                "ai_task", "generate_data", request, blocking=True, return_response=True
            )
        except HomeAssistantError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="scan_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        data = (result or {}).get("data")
        return {"values": _clean_scan(kind, data if isinstance(data, dict) else {})}

    async def attach_receipt(call: ServiceCall) -> None:
        coordinator, entity = _resolve(hass, call.data["entity_id"])
        receipt = await _checked_receipt(hass, call.data["receipt"])
        if call.data.get("log_entry_id"):
            old = store.attach_to_log(
                coordinator.config_entry.entry_id, call.data["log_entry_id"], receipt
            )
        elif entity.config_subentry_id:
            old = store.attach_to_service(entity.config_subentry_id, receipt)
        else:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="attach_target_missing"
            )
        if old is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="attach_target_not_found"
            )
        if old and old != receipt:
            await async_delete(hass, [old])
        await coordinator.async_refresh()

    async def delete_log_entry(call: ServiceCall) -> None:
        coordinator, _ = _resolve(hass, call.data["entity_id"])
        entry = store.delete_log(
            coordinator.config_entry.entry_id, call.data["log_entry_id"]
        )
        if entry is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="attach_target_not_found"
            )
        if entry.get("receipt"):
            await async_delete(hass, [entry["receipt"]])
        await coordinator.async_refresh()

    for name, handler, schema in (
        (SERVICE_SET_ODOMETER, set_odometer, SET_ODOMETER_SCHEMA),
        (SERVICE_ADD_FUEL, add_fuel, ADD_FUEL_SCHEMA),
        (SERVICE_ADD_CHARGE, add_charge, ADD_CHARGE_SCHEMA),
        (SERVICE_COMPLETE_SERVICE, complete_service, COMPLETE_SERVICE_SCHEMA),
        ("attach_receipt", attach_receipt, ATTACH_RECEIPT_SCHEMA),
        ("delete_log_entry", delete_log_entry, DELETE_LOG_ENTRY_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=schema)
    for name, handler, schema in (
        ("upload_receipt", upload_receipt, UPLOAD_RECEIPT_SCHEMA),
        ("scan_receipt", scan_receipt, SCAN_RECEIPT_SCHEMA),
    ):
        hass.services.async_register(
            DOMAIN, name, handler, schema=schema, supports_response=SupportsResponse.ONLY
        )

    hass.http.register_view(ReceiptView())

    async def _cleanup(_: Any = None) -> None:
        removed = await async_cleanup_orphans(hass, store.referenced_receipts())
        if removed:
            _LOGGER.debug("Removed %s unused uploaded receipts", removed)

    hass.async_create_task(_cleanup())
    async_track_time_interval(
        hass, _cleanup, datetime.timedelta(hours=24), cancel_on_shutdown=True
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: VehicleConfigEntry) -> bool:
    """Set up a vehicle from a config entry."""
    store: VehicleStore = hass.data[DOMAIN]["store"]
    coordinator = VehicleCoordinator(hass, entry, store)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    coordinator.start_tracking()

    _async_prepare_devices(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    return True


def _async_prepare_devices(
    hass: HomeAssistant, entry: VehicleConfigEntry, coordinator: VehicleCoordinator
) -> None:
    """Create the vehicle device and unlink it from service items.

    Service items have their own devices (linked via ``via_device``). Earlier
    versions attached the shared vehicle device to every service item, which
    showed all vehicle entities under each item.
    """
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Vehicle",
        model=coordinator.fuel_type.value.capitalize(),
    )
    if hasattr(device, "config_subentry_id"):
        # Home Assistant 2026.10+: a device belongs to exactly one subentry.
        if device.config_subentry_id is not None:
            dev_reg.async_update_device(device.id, new_config_subentry_id=None)
        return
    for subentry_id in device.config_entries_subentries.get(entry.entry_id, set()):
        if subentry_id is not None:
            dev_reg.async_update_device(
                device.id,
                remove_config_entry_id=entry.entry_id,
                remove_config_subentry_id=subentry_id,
            )


async def _async_entry_updated(hass: HomeAssistant, entry: VehicleConfigEntry) -> None:
    """Reload on config or subentry changes and drop history of deleted items."""
    store: VehicleStore = hass.data[DOMAIN]["store"]
    known = {
        sid
        for entries in hass.config_entries.async_entries(DOMAIN)
        for sid, sub in entries.subentries.items()
        if sub.subentry_type == SUBENTRY_TYPE_SERVICE
    }
    await async_delete(hass, store.prune_services(known))
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: VehicleConfigEntry) -> bool:
    """Unload a vehicle."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: VehicleConfigEntry) -> None:
    """Delete stored data of a removed vehicle."""
    store: VehicleStore = hass.data[DOMAIN]["store"]
    receipts: list[str] = []
    for sid in entry.subentries:
        receipts += store.remove_service(sid)
    receipts += store.remove_vehicle(entry.entry_id)
    await async_delete(hass, receipts)
