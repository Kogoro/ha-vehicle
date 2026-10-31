#!/usr/bin/env python3
"""Create a dev user and demo vehicles in a fresh Home Assistant test instance.

Usage: python3 dev/seed.py [base_url]     (default http://localhost:8123)
Login afterwards with dev / dev. Safe to run repeatedly.
"""

import datetime
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8123").rstrip("/")
CLIENT_ID = BASE + "/"
USER = PASSWORD = "dev"


def call(method, path, body=None, token=None, form=False):
    data = None
    headers = {}
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as err:
        if path == "/api/onboarding":
            raise
        raise SystemExit(f"{method} {path} -> {err.code}: {err.read().decode()[:500]}") from None
    return json.loads(raw) if raw else None


def wait_for_ha():
    """Return the onboarding steps; an already onboarded instance answers 404."""
    for _ in range(120):
        try:
            return [{"step": s["step"], "done": s["done"]} for s in call("GET", "/api/onboarding")]
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return [{"step": "user", "done": True}]
            time.sleep(2)
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(2)
    raise SystemExit(f"Home Assistant not reachable at {BASE}")


def token_from_code(code):
    return call(
        "POST", "/auth/token",
        {"grant_type": "authorization_code", "code": code, "client_id": CLIENT_ID},
        form=True,
    )["access_token"]


def login():
    steps = {s["step"]: s["done"] for s in wait_for_ha()}
    if not steps.get("user"):
        code = call("POST", "/api/onboarding/users", {
            "client_id": CLIENT_ID, "name": "Dev", "username": USER,
            "password": PASSWORD, "language": "en",
        })["auth_code"]
        token = token_from_code(code)
        for step, body in (("core_config", {}), ("analytics", {}),
                           ("integration", {"client_id": CLIENT_ID, "redirect_uri": CLIENT_ID})):
            if not steps.get(step):
                call("POST", f"/api/onboarding/{step}", body, token=token)
        return token
    flow = call("POST", "/auth/login_flow", {
        "client_id": CLIENT_ID, "handler": ["homeassistant", None], "redirect_uri": CLIENT_ID,
    })
    result = call("POST", f"/auth/login_flow/{flow['flow_id']}", {
        "client_id": CLIENT_ID, "username": USER, "password": PASSWORD,
    })
    if result.get("type") != "create_entry":
        raise SystemExit("Login failed (is the dev user's password still 'dev'?)")
    return token_from_code(result["result"])


def main():
    token = login()
    def api(method, path, body=None):
        return call(method, path, body, token=token)

    existing = {e["title"]: e["entry_id"] for e in api("GET", "/api/config/config_entries/entry?domain=vehicle")}
    today = datetime.date.today()

    def ago(days):
        return (today - datetime.timedelta(days=days)).isoformat()

    if not api("GET", "/api/config/config_entries/entry?domain=fake_ai_task"):
        flow = api("POST", "/api/config/config_entries/flow", {"handler": "fake_ai_task"})
        if flow["type"] != "create_entry":
            api("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", {})
        print("Fake AI task provider created (canned values, dev only)")

    vehicles = {
        "Golf": {
            "data": {"fuel_type": "petrol", "warn_days": 30, "warn_km": 1000},
            "items": [
                {"name": "Oil change", "interval_days": 365, "interval_km": 15000,
                 "last_service_date": ago(200), "last_service_odometer": 36000},
                {"name": "Tire check", "interval_days": 90, "last_service_date": ago(120)},
                {"name": "Inspection", "interval_days": 730, "interval_km": 30000,
                 "last_service_date": ago(400), "last_service_odometer": 20000},
            ],
        },
        "Tesla": {
            "data": {"fuel_type": "electric", "warn_days": 30, "warn_km": 1000,
                     "odometer_entity": "input_number.tesla_odometer"},
            "items": [
                {"name": "Cabin filter", "interval_days": 365, "last_service_date": ago(30)},
                {"name": "Brake fluid", "interval_days": 730, "interval_km": 60000,
                 "last_service_date": ago(700), "last_service_odometer": 5000},
            ],
        },
    }

    for name, spec in vehicles.items():
        if name in existing:
            print(f"{name}: already exists, skipping")
            continue
        flow = api("POST", "/api/config/config_entries/flow", {"handler": "vehicle"})
        done = api("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", {"name": name, **spec["data"]})
        entry_id = done["result"]["entry_id"]
        for item in spec["items"]:
            flow = api("POST", "/api/config/config_entries/subentries/flow", {"handler": [entry_id, "service_item"]})
            api("POST", f"/api/config/config_entries/subentries/flow/{flow['flow_id']}", item)
        print(f"{name}: created with {len(spec['items'])} service items")

        slug = name.lower()
        entity = f"sensor.{slug}_odometer"
        time.sleep(3)  # let the entry reload after the subentries
        if name == "Golf":
            api("POST", "/api/services/vehicle/set_odometer", {"entity_id": entity, "odometer": 48200})
            log = [(80, 43400, 38.4, 1.789), (60, 44450, 41.2, 1.759),
                   (40, 45500, 36.0, 1.739), (20, 46550, 39.8, 1.799), (5, 47500, 40.5, 1.839)]
            for days, odo, liters, price in log:
                api("POST", "/api/services/vehicle/add_fuel", {
                    "entity_id": entity, "date": ago(days), "odometer": odo,
                    "liters": liters, "price_per_liter": price})
        else:
            for days, odo, kwh, price in [(30, 11500, 45.0, 0.34), (14, 11800, 52.5, 0.29), (3, 12000, 40.0, 0.36)]:
                api("POST", "/api/services/vehicle/add_charge", {
                    "entity_id": entity, "date": ago(days), "odometer": odo,
                    "kwh": kwh, "price_per_kwh": price})

    print(f"\nReady: {BASE}  (login dev / dev)\nDashboard: {BASE}/dashboard-vehicle")


main()
