"""End-to-end tests for the Vehicle integration."""

import datetime

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.vehicle.const import DOMAIN


async def _setup(hass: HomeAssistant, fuel_type="petrol", **data) -> MockConfigEntry:
    today = dt_util.now().date()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Golf",
        unique_id="golf",
        data={"fuel_type": fuel_type, "warn_days": 30, "warn_km": 1000, **data},
        subentries_data=[
            ConfigSubentryData(
                data={
                    "interval_days": 365,
                    "interval_km": 15000,
                    "last_service_date": (today - datetime.timedelta(days=100)).isoformat(),
                    "last_service_odometer": 10000.0,
                },
                subentry_type="service_item",
                title="Oil change",
                subentry_id="oil",
                unique_id=None,
            ),
            ConfigSubentryData(
                data={
                    "interval_days": 30,
                    "last_service_date": (today - datetime.timedelta(days=40)).isoformat(),
                },
                subentry_type="service_item",
                title="Tire check",
                subentry_id="tires",
                unique_id=None,
            ),
        ],
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return entry


def _entity(hass, platform, uid_suffix):
    reg = er.async_get(hass)
    return next(
        e.entity_id
        for e in reg.entities.values()
        if e.platform == DOMAIN and e.domain == platform and e.unique_id.endswith(uid_suffix)
    )


async def test_service_items_and_entities(hass: HomeAssistant) -> None:
    """Items get status, days and km sensors, overdue binary sensor and button."""
    await _setup(hass)

    await hass.services.async_call(
        DOMAIN, "set_odometer", {"entity_id": _entity(hass, "sensor", "_odometer"), "odometer": 20000}, blocking=True
    )
    status = hass.states.get(_entity(hass, "sensor", "oil_status"))
    assert status.state == "ok"
    assert status.attributes["km_remaining"] == 5000.0
    assert status.attributes["days_remaining"] == 265
    assert hass.states.get(_entity(hass, "sensor", "oil_km_remaining")).state == "5000.0"

    tires = hass.states.get(_entity(hass, "sensor", "tires_status"))
    assert tires.state == "overdue"
    assert hass.states.get(_entity(hass, "binary_sensor", "tires_overdue")).state == "on"
    assert hass.states.get(_entity(hass, "binary_sensor", "oil_overdue")).state == "off"
    # no km interval -> no km sensor for tires
    with pytest.raises(StopIteration):
        _entity(hass, "sensor", "tires_km_remaining")


async def test_complete_service(hass: HomeAssistant) -> None:
    """Pressing the button records a completion and fires an event."""
    await _setup(hass)
    events = async_capture_events(hass, "vehicle_service_completed")
    await hass.services.async_call(
        DOMAIN, "set_odometer", {"entity_id": _entity(hass, "sensor", "_odometer"), "odometer": 12345}, blocking=True
    )
    await hass.services.async_call(
        "button", "press", {"entity_id": _entity(hass, "button", "tires_complete")}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(_entity(hass, "sensor", "tires_status")).state == "due_soon"  # 30d interval = warn window
    assert len(events) == 1 and events[0].data["service"] == "Tire check"

    await hass.services.async_call(
        DOMAIN,
        "complete_service",
        {"entity_id": _entity(hass, "sensor", "oil_status"), "odometer": 15000},
        blocking=True,
    )
    status = hass.states.get(_entity(hass, "sensor", "oil_status"))
    assert status.attributes["last_odometer"] == 15000
    assert status.attributes["next_due_odometer"] == 30000


async def test_fuel_log_and_stats(hass: HomeAssistant) -> None:
    """Fuel entries produce consumption and cost statistics."""
    await _setup(hass)
    entity = _entity(hass, "sensor", "_odometer")
    today = dt_util.now().date()
    for odo, liters, price in ((1000, 40, 1.5), (1500, 20, 1.5), (2000, 15, 1.6)):
        await hass.services.async_call(
            DOMAIN,
            "add_fuel",
            {"entity_id": entity, "liters": liters, "price_per_liter": price, "odometer": odo},
            blocking=True,
        )
    assert hass.states.get(entity).state == "2000.0"
    assert float(hass.states.get(_entity(hass, "sensor", "_fuel_consumption")).state) == 3.5
    assert float(hass.states.get(_entity(hass, "sensor", "_cost_per_km")).state) == pytest.approx(0.0532, abs=1e-3)
    assert float(hass.states.get(_entity(hass, "sensor", "_monthly_cost")).state) == 114.0
    assert float(hass.states.get(_entity(hass, "sensor", "_fuel_price")).state) == 1.6
    # total_cost alone derives the price
    await hass.services.async_call(
        DOMAIN, "add_fuel", {"entity_id": entity, "liters": 10, "total_cost": 17.0}, blocking=True
    )
    assert float(hass.states.get(_entity(hass, "sensor", "_fuel_price")).state) == 1.7
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "add_fuel", {"entity_id": entity, "liters": 10}, blocking=True)
    assert len(hass.states.get(entity).attributes["recent_log"]) == 4
    assert today.isoformat() == hass.states.get(entity).attributes["recent_log"][0]["date"]
    assert "full" not in hass.states.get(entity).attributes["recent_log"][0]

    with pytest.raises(StopIteration):
        _entity(hass, "sensor", "_energy_consumption")
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "add_charge", {"entity_id": entity, "kwh": 10}, blocking=True
        )


async def test_electric_vehicle(hass: HomeAssistant) -> None:
    """Electric vehicles log charges and get energy consumption."""
    await _setup(hass, fuel_type="electric")
    entity = _entity(hass, "sensor", "_odometer")
    for odo, kwh in ((100, 30), (300, 40)):
        await hass.services.async_call(
            DOMAIN, "add_charge", {"entity_id": entity, "kwh": kwh, "price_per_kwh": 0.3, "odometer": odo}, blocking=True
        )
    assert float(hass.states.get(_entity(hass, "sensor", "_energy_consumption")).state) == 20.0
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "add_fuel", {"entity_id": entity, "liters": 5}, blocking=True)


async def test_linked_odometer_and_decrease(hass: HomeAssistant) -> None:
    """A linked sensor wins over manual values (miles are converted); manual never decreases."""
    hass.states.async_set("sensor.car_odo", "1000", {"unit_of_measurement": "mi"})
    await _setup(hass, odometer_entity="sensor.car_odo")
    entity = _entity(hass, "sensor", "_odometer")
    assert float(hass.states.get(entity).state) == pytest.approx(1609.3, abs=0.1)
    assert hass.states.get(entity).attributes["source"] == "sensor"

    hass.states.async_set("sensor.car_odo", "unavailable")
    await hass.async_block_till_done()
    await hass.services.async_call(DOMAIN, "set_odometer", {"entity_id": entity, "odometer": 500}, blocking=True)
    assert hass.states.get(entity).attributes["source"] == "manual"
    assert float(hass.states.get(entity).state) == 500
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "set_odometer", {"entity_id": entity, "odometer": 400}, blocking=True)
    await hass.services.async_call(
        DOMAIN, "set_odometer", {"entity_id": entity, "odometer": 400, "allow_decrease": True}, blocking=True
    )
    assert float(hass.states.get(entity).state) == 400


async def test_config_flow(hass: HomeAssistant) -> None:
    """A vehicle can be added through the UI flow, duplicates are rejected."""
    await async_setup_component(hass, DOMAIN, {})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Tesla", "fuel_type": "electric", "warn_days": 30, "warn_km": 1000},
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "Tesla"
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "tesla", "fuel_type": "electric", "warn_days": 30, "warn_km": 1000},
    )
    assert result["type"] == "abort"

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    flow = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "service_item"), context={"source": "user"}
    )
    bad = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"name": "Brakes"})
    assert bad["errors"] == {"base": "interval_required"}
    ok = await hass.config_entries.subentries.async_configure(
        flow["flow_id"], {"name": "Brakes", "interval_km": 30000}
    )
    assert ok["type"] == "create_entry"
    await hass.async_block_till_done()
    assert hass.states.get(_entity(hass, "sensor", "_odometer")) is not None


def _device_subentries(device, entry_id) -> set:
    """Subentry ids a device is linked to (works before and after HA 2026.10)."""
    if hasattr(device, "config_subentry_id"):
        return {device.config_subentry_id}
    return set(device.config_entries_subentries[entry_id])


def _find_device(dev_reg, entry_id, identifier):
    """Look a device up by identifier (works before and after HA 2026.10)."""
    if hasattr(dev_reg, "async_get_device_by_identifier"):
        return dev_reg.async_get_device_by_identifier(
            identifier, entry_id
        ) or dev_reg.async_get_child_device_by_identifier(identifier, entry_id)
    return dev_reg.async_get_device(identifiers={identifier})


async def test_service_items_have_own_devices(hass: HomeAssistant) -> None:
    """Items get their own device linked to the vehicle; the vehicle device is not touched."""
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.helpers import device_registry as dr

    entry = await _setup(hass)
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    vehicle_dev = _find_device(dev_reg, entry.entry_id, (DOMAIN, entry.entry_id))
    assert vehicle_dev is not None
    odometer = ent_reg.async_get(_entity(hass, "sensor", "_odometer"))
    cost = ent_reg.async_get(_entity(hass, "sensor", "_cost_per_km"))
    assert odometer.device_id == cost.device_id == vehicle_dev.id

    for item in ("oil", "tires"):
        item_dev = _find_device(dev_reg, entry.entry_id, (DOMAIN, f"{entry.entry_id}_{item}"))
        assert item_dev is not None and item_dev.id != vehicle_dev.id
        assert item_dev.via_device_id == vehicle_dev.id
        status = ent_reg.async_get(_entity(hass, "sensor", f"{item}_status"))
        assert status.device_id == item_dev.id and status.config_subentry_id == item
    assert hass.states.get(_entity(hass, "sensor", "oil_status")).name == "Golf Oil change"
    assert _device_subentries(vehicle_dev, entry.entry_id) == {None}

    # adding another item later leaves the vehicle device and its entities alone
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(data={"interval_km": 40000}, subentry_type="service_item", title="Brakes", unique_id=None),
    )
    await hass.async_block_till_done()
    assert _device_subentries(dev_reg.async_get(vehicle_dev.id), entry.entry_id) == {None}
    assert ent_reg.async_get(odometer.entity_id).device_id == vehicle_dev.id
    brakes = ent_reg.async_get(next(s.entity_id for s in hass.states.async_all("sensor") if s.name == "Golf Brakes"))
    assert brakes.device_id != vehicle_dev.id


async def test_old_shared_device_is_unlinked_from_items(hass: HomeAssistant) -> None:
    """Upgrading from the shared-device layout removes the subentry links from the vehicle device."""
    from homeassistant.helpers import device_registry as dr

    entry = MockConfigEntry(
        domain=DOMAIN, title="Old", unique_id="old",
        data={"fuel_type": "petrol", "warn_days": 30, "warn_km": 1000},
        subentries_data=[ConfigSubentryData(
            data={"interval_days": 30}, subentry_type="service_item", title="Item",
            subentry_id="sub1", unique_id=None)],
    )
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    old = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, config_subentry_id="sub1", identifiers={(DOMAIN, entry.entry_id)}
    )
    assert "sub1" in _device_subentries(old, entry.entry_id)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    new = dev_reg.async_get(old.id)
    assert "sub1" not in _device_subentries(new, entry.entry_id)
