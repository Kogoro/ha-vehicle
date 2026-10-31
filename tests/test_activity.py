"""Tests for the activity list, monthly costs, status events and the blueprint."""

import datetime
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_mock_service,
)

from custom_components.vehicle.const import DOMAIN

from .test_vehicle import _entity, _setup


async def test_monthly_costs_and_activity(hass: HomeAssistant) -> None:
    """Service completions count towards the monthly service cost and appear in the activity list."""
    await _setup(hass)
    odometer = _entity(hass, "sensor", "_odometer")
    status = _entity(hass, "sensor", "oil_status")
    today = dt_util.now().date()
    last_month = (today.replace(day=1) - datetime.timedelta(days=3)).isoformat()

    await hass.services.async_call(
        DOMAIN, "add_fuel", {"entity_id": odometer, "liters": 40, "price_per_liter": 1.5, "odometer": 1000}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, "complete_service", {"entity_id": status, "cost": 289.5, "odometer": 1200}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN,
        "complete_service",
        {"entity_id": _entity(hass, "sensor", "tires_status"), "cost": 80, "date": last_month},
        blocking=True,
    )

    assert float(hass.states.get(_entity(hass, "sensor", "_monthly_service_cost")).state) == 289.5
    monthly = hass.states.get(_entity(hass, "sensor", "_monthly_cost"))
    assert float(monthly.state) == 60.0
    assert monthly.attributes["fuel"] == 60.0 and monthly.attributes["energy"] == 0.0

    activity = hass.states.get(odometer).attributes["activity"]
    assert [(a["kind"], a.get("name")) for a in activity] == [
        ("service", "Oil change"),
        ("fuel", None),
        ("service", "Tire check"),
    ]
    assert activity[0]["cost"] == 289.5 and activity[0]["odometer"] == 1200


async def test_status_events_fire_once_on_transition(hass: HomeAssistant) -> None:
    """due_soon and overdue events fire when an item changes status, not for the initial state."""
    await _setup(hass)
    due_soon = async_capture_events(hass, "vehicle_service_due_soon")
    overdue = async_capture_events(hass, "vehicle_service_overdue")
    odometer = _entity(hass, "sensor", "_odometer")
    assert not due_soon and not overdue  # the overdue tire check is not announced on startup

    # oil change: last at 10,000 km + 15,000 interval -> due at 25,000; warn window is 1,000 km
    await hass.services.async_call(DOMAIN, "set_odometer", {"entity_id": odometer, "odometer": 24500}, blocking=True)
    assert [e.data["service"] for e in due_soon] == ["Oil change"] and not overdue
    assert due_soon[0].data["km_remaining"] == 500.0

    await hass.services.async_call(DOMAIN, "set_odometer", {"entity_id": odometer, "odometer": 24600}, blocking=True)
    assert len(due_soon) == 1  # still due soon: no repeat

    await hass.services.async_call(DOMAIN, "set_odometer", {"entity_id": odometer, "odometer": 25500}, blocking=True)
    assert [e.data["service"] for e in overdue] == ["Oil change"] and len(due_soon) == 1


async def test_blueprint_notifies(hass: HomeAssistant) -> None:
    """The bundled blueprint is installed and reacts to the events."""
    await _setup(hass)
    assert Path(hass.config.path("blueprints", "automation", DOMAIN, "service_due.yaml")).is_file()
    calls = async_mock_service(hass, "persistent_notification", "create")
    assert await async_setup_component(
        hass,
        "automation",
        {"automation": {"use_blueprint": {"path": f"{DOMAIN}/service_due.yaml", "input": {"notify_due_soon": False}}}},
    )
    await hass.async_block_till_done()

    data = {"vehicle": "Golf", "service": "Tire check", "days_remaining": -5, "km_remaining": None}
    hass.bus.async_fire("vehicle_service_due_soon", data)
    await hass.async_block_till_done()
    assert not calls  # switched off in the blueprint input

    hass.bus.async_fire("vehicle_service_overdue", data)
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0].data["title"] == "Golf"
    assert "Tire check is overdue (-5 days)" in " ".join(calls[0].data["message"].split())


async def _import(hass, entry, categories, items, last_date="2026-10-01"):
    flow = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "import_items"), context={"source": "user"}
    )
    step = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"categories": categories})
    options = [o["value"] for o in step["data_schema"].schema["items"].config["options"]]
    labels = {o["value"]: o["label"] for o in step["data_schema"].schema["items"].config["options"]}
    if items is None:
        return options, labels
    step = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"items": items})
    assert step["step_id"] == "configure"
    return await hass.config_entries.subentries.async_configure(flow["flow_id"], {"last_service_date": last_date})


async def test_import_common_service_items(hass: HomeAssistant) -> None:
    """The import action offers catalog items that fit the drive type and creates service items."""
    entry = await _setup(hass)  # petrol, already has "Oil change" and "Tire check"
    options, labels = await _import(hass, entry, ["engine", "tires"], None)
    assert "spark_plugs" in options and "oil_change" in options
    assert "fuel_filter" not in options  # diesel only
    assert labels["oil_change"] == "Oil and filter change (1 y / 15 000 km)"
    assert labels["tire_change"].startswith("Seasonal tire change (6 mo")

    result = await _import(hass, entry, ["engine", "tires"], ["oil_change", "tire_rotation"])
    assert result["type"] == "abort" and result["reason"] == "import_success"
    assert result["description_placeholders"] == {"count": "2"}
    await hass.async_block_till_done()

    created = {s.title: dict(s.data) for s in entry.subentries.values() if s.subentry_type == "service_item"}
    assert created["Oil and filter change"] == {
        "description": "Change engine oil and oil filter",
        "icon": "mdi:oil",
        "interval_days": 365,
        "interval_km": 15000,
        "last_service_date": "2026-10-01",
    }
    assert "interval_days" not in created["Tire rotation"] and created["Tire rotation"]["interval_km"] == 10000
    assert hass.states.get("sensor.golf_oil_and_filter_change") is not None

    _, labels = await _import(hass, entry, ["engine"], None)
    assert labels["oil_change"].endswith("• exists")


async def test_import_filters_by_drive_type(hass: HomeAssistant) -> None:
    """Electric vehicles do not get engine items, but get electric ones."""
    entry = await _setup(hass, fuel_type="electric")
    options, _ = await _import(hass, entry, ["engine", "electric"], None)
    assert "oil_change" not in options and "spark_plugs" not in options
    assert {"gearbox_oil", "hv_battery_check"} <= set(options)

    flow = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "import_items"), context={"source": "user"}
    )
    offered = [o["value"] for o in flow["data_schema"].schema["categories"].config["options"]]
    assert "electric" in offered
    petrol = await _setup(hass)
    assert petrol is not None


async def test_catalog_is_consistent() -> None:
    """Every catalog entry is complete and has a German name."""
    import json

    from custom_components.vehicle.catalog import CATALOG_PATH

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    ids = [i["id"] for c in catalog["categories"] for i in c["items"]]
    assert len(ids) == len(set(ids))
    for category in catalog["categories"]:
        assert {"en", "de"} <= set(category["name"])
        for item in category["items"]:
            assert item["interval_days"] or item["interval_km"], item["id"]
            assert {"en", "de"} <= set(item["name"]) and {"en", "de"} <= set(item["description"])
            assert item["applies_to"] and set(item["applies_to"]) <= {"petrol", "diesel", "hybrid", "electric"}
