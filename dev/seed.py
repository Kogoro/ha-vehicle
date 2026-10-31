#!/usr/bin/env python3
"""Create a dev user and demo vehicles in a fresh Home Assistant test instance.

Usage: python3 dev/seed.py [base_url]     (default http://localhost:8123)
Login afterwards with dev / dev. Safe to run repeatedly.
"""

import base64
import datetime
import json
import os
import socket
import ssl
import struct
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


class WebSocket:
    """Tiny stdlib WebSocket client, just enough for Home Assistant's API."""

    def __init__(self, base, token):
        url = urllib.parse.urlparse(base)
        secure = url.scheme == "https"
        port = url.port or (443 if secure else 80)
        sock = socket.create_connection((url.hostname, port), timeout=60)
        if secure:
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=url.hostname)
        self.sock = sock
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall((
            f"GET /api/websocket HTTP/1.1\r\nHost: {url.hostname}:{port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode())
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = sock.recv(1024)
            if not chunk:
                raise SystemExit("WebSocket handshake failed")
            header += chunk
        self.buffer = header.split(b"\r\n\r\n", 1)[1]
        self.next_id = 1
        self.recv_json()  # auth_required
        self.send_json({"type": "auth", "access_token": token})
        if self.recv_json().get("type") != "auth_ok":
            raise SystemExit("WebSocket authentication failed")

    def _read(self, size):
        while len(self.buffer) < size:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise SystemExit("WebSocket closed unexpectedly")
            self.buffer += chunk
        data, self.buffer = self.buffer[:size], self.buffer[size:]
        return data

    def _send_frame(self, opcode, payload):
        header = bytes([0x80 | opcode])
        size = len(payload)
        if size < 126:
            header += bytes([0x80 | size])
        elif size < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", size)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", size)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def send_json(self, message):
        self._send_frame(1, json.dumps(message).encode())

    def recv_json(self):
        message = b""
        while True:
            first, second = self._read(2)
            opcode, size = first & 0x0F, second & 0x7F
            if size == 126:
                size = struct.unpack(">H", self._read(2))[0]
            elif size == 127:
                size = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(size)
            if opcode == 9:  # ping
                self._send_frame(10, payload)
            elif opcode == 8:
                raise SystemExit("WebSocket closed by Home Assistant")
            else:
                message += payload
                if first & 0x80:  # final fragment
                    return json.loads(message)

    def call(self, message_type, **fields):
        message_id, self.next_id = self.next_id, self.next_id + 1
        self.send_json({"id": message_id, "type": message_type, **fields})
        while True:
            reply = self.recv_json()
            if reply.get("id") == message_id and reply.get("type") == "result":
                if not reply.get("success"):
                    raise SystemExit(f"{message_type} failed: {reply.get('error')}")
                return reply.get("result")

    def close(self):
        self.sock.close()


DASHBOARD_URL_PATH = "dashboard-vehicle"
DASHBOARD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "dashboards", "vehicle.json")


def ensure_dashboard(token):
    """Make sure a 'Vehicle' dashboard exists, whatever configuration.yaml says."""
    ws = WebSocket(BASE, token)
    try:
        existing = {d["url_path"]: d for d in ws.call("lovelace/dashboards/list")}
        if DASHBOARD_URL_PATH in existing:
            print(f"Dashboard: already present ({existing[DASHBOARD_URL_PATH].get('mode', 'yaml')} mode)")
            return
        with open(DASHBOARD_FILE, encoding="utf-8") as handle:
            config = json.load(handle)
        ws.call(
            "lovelace/dashboards/create",
            url_path=DASHBOARD_URL_PATH, title="Vehicle", icon="mdi:car",
            show_in_sidebar=True, require_admin=False, mode="storage",
        )
        ws.call("lovelace/config/save", url_path=DASHBOARD_URL_PATH, config=config)
        print("Dashboard: created 'Vehicle' (sidebar entry, storage mode)")
    finally:
        ws.close()


def start_flow(api, handler):
    """Start a config flow; explain clearly when Home Assistant does not know the integration."""
    try:
        return api("POST", "/api/config/config_entries/flow", {"handler": handler})
    except SystemExit as err:
        if "Invalid handler" not in str(err):
            raise
        raise SystemExit(
            f"Home Assistant does not know the integration '{handler}'.\n"
            f"  - It must be inside the config directory of the running instance:\n"
            f"    <config>/custom_components/{handler}/manifest.json\n"
            f"  - Docker:  docker compose -f dev/docker-compose.yml up -d   (mounts it for you)\n"
            f"  - Local:   dev/run-local.sh                                 (links it for you)\n"
            f"  - If it is there, the integration failed to load: check the Home Assistant log for\n"
            f"    'Unable to prepare setup', 'Error importing' or 'requires Home Assistant'.\n"
            f"  Restart Home Assistant after adding the folder."
        ) from None


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
        try:
            flow = start_flow(api, "fake_ai_task")
            if flow["type"] != "create_entry":
                api("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", {})
            print("Fake AI task provider created (canned values, dev only)")
        except SystemExit as err:
            # optional extra: needs Home Assistant 2025.8+ (ai_task) and the dev config folder
            print(f"  (skipping the fake AI provider: {str(err).splitlines()[0]})")

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
        flow = start_flow(api, "vehicle")
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

    ensure_dashboard(token)

    print(f"\nReady: {BASE}  (login dev / dev)\nDashboard: {BASE}/dashboard-vehicle")


main()
