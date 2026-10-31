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
