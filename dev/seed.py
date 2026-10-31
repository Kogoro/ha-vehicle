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


def call(method, path, body=None, token=None, form=False, retries=6):
    """HTTP helper. Retries timeouts: Home Assistant is slow while it starts up."""
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
    for attempt in range(retries):
        req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
            return json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            detail = err.read().decode()[:500]
            if path == "/api/onboarding":
                raise
            raise SystemExit(f"{method} {path} -> {err.code}: {detail}") from None
        except (TimeoutError, urllib.error.URLError, ConnectionError, OSError):
            if attempt == retries - 1:
                raise
            print(f"  ... waiting for Home Assistant ({method} {path})")
            time.sleep(5)


def wait_for_ha():
    """Return the onboarding steps; an already onboarded instance answers 404."""
    for _ in range(180):
        try:
            return [{"step": s["step"], "done": s["done"]} for s in call("GET", "/api/onboarding", retries=1)]
        except urllib.error.HTTPError as err:
            if err.code == 404 and providers_ready():
                return [{"step": "user", "done": True}]
            time.sleep(2)
        except (TimeoutError, urllib.error.URLError, ConnectionError, OSError):
            time.sleep(2)
    raise SystemExit(f"Home Assistant not reachable at {BASE}")


def providers_ready():
    """The auth component answers once Home Assistant is far enough started."""
    try:
        call("GET", "/auth/providers", retries=1)
    except (SystemExit, TimeoutError, urllib.error.URLError, ConnectionError, OSError):
        return False
    return True


def token_from_code(code):
    return call(
        "POST", "/auth/token",
        {"grant_type": "authorization_code", "code": code, "client_id": CLIENT_ID},
        form=True,
    )["access_token"]


def login_with_password():
    flow = call("POST", "/auth/login_flow", {
        "client_id": CLIENT_ID, "handler": ["homeassistant", None], "redirect_uri": CLIENT_ID,
    })
    result = call("POST", f"/auth/login_flow/{flow['flow_id']}", {
        "client_id": CLIENT_ID, "username": USER, "password": PASSWORD,
    })
    if result.get("type") != "create_entry":
        raise SystemExit("Login failed. The instance has another 'dev' user or a changed password; "
                         "reset it by deleting dev/config/.storage and restarting.")
    return token_from_code(result["result"])


def create_onboarding_user():
    """Create the first user. Returns (token, username)."""
    # An earlier interrupted run can leave the user created but the wizard step
    # unfinished. The step can only be completed by creating a user, so fall
    # back to dev2, dev3, ... in that case.
    for username in [USER, *[f"{USER}{n}" for n in range(2, 6)]]:
        try:
            code = call("POST", "/api/onboarding/users", {
                "client_id": CLIENT_ID, "name": username.capitalize(), "username": username,
                "password": PASSWORD, "language": "en",
            }, retries=1)["auth_code"]
            return token_from_code(code), username
        except SystemExit as err:
            if "username_already_exists" not in str(err):
                raise
    raise SystemExit("Could not finish onboarding. Delete dev/config/.storage and restart Home Assistant.")


def login():
    steps = {s["step"]: s["done"] for s in wait_for_ha()}
    token = None
    if not steps.get("user"):
        token, username = create_onboarding_user()
        if username != USER:
            print(f"  (the user '{USER}' existed from an interrupted run; onboarding finished with '{username}')")
            print(f"  log in as {username} / {PASSWORD}  (or {USER} / {PASSWORD})")
    if token is None:
        token = login_with_password()
    for step, body in (("core_config", {}), ("analytics", {}),
                       ("integration", {"client_id": CLIENT_ID, "redirect_uri": CLIENT_ID})):
        if steps.get(step) is False:
            try:
                call("POST", f"/api/onboarding/{step}", body, token=token)
            except SystemExit as err:
                print(f"  (onboarding step {step} skipped: {err})")
    return token


def wait_until_running(token):
    """Block until Home Assistant has finished starting all integrations."""
    for _ in range(120):
        try:
            if call("GET", "/api/config", token=token, retries=1).get("state") == "RUNNING":
                return
        except (SystemExit, TimeoutError, urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(3)
    print("  (Home Assistant is still starting; continuing anyway)")


def main():
    token = login()
    wait_until_running(token)

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
