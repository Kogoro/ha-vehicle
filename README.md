# Vehicle — Basic Vehicle Management for Home Assistant

[![HACS][hacs-badge]][hacs-url]
[![License][license-badge]][license-url]

A custom Home Assistant integration for tracking your vehicles: service and maintenance intervals, fuel and charging costs, and mileage. Modelled after [ha-task](https://github.com/Kogoro/ha-task): one config entry per vehicle, service items as subentries, UI configuration only.

## Features

- **Multiple vehicles** — one config entry (and one device) per vehicle: petrol, diesel, hybrid or electric.
- **Service & maintenance** — items such as oil change, tires or inspection with a day interval, a km interval, or both. An item is due when **either** limit is reached.
- **Mileage** — link an existing odometer sensor (miles are converted to km) or enter readings manually. Fuel/charge logs and completed services raise the manual odometer automatically.
- **Fuel & charging log** — log refuels (liters) and charges (kWh) with cost and odometer. Prices per liter / kWh are recorded with every entry for trends. Get consumption (L/100 km, kWh/100 km), cost per km and cost this month.
- **Receipts and invoices** — attach a photo or PDF to a fuel/charge entry or a completed service. Optionally let an AI task entity read date, amounts and prices from it to pre-fill the form.
- **Events** — `vehicle_service_overdue` and `vehicle_service_completed` for automations.
- **Lovelace cards** — `vehicle-card` (overview) and `vehicle-log-card` (add fuel/charge), both with a visual editor. Single values can be shown with any standard HA card.

![Dashboard with two demo vehicles](docs/dashboard.png)

## Installation

### HACS (recommended)

1. HACS → **Integrations** → ⋮ → **Custom repositories**.
2. Add `https://github.com/Kogoro/ha-vehicle` with category **Integration**.
3. Install **Vehicle** and restart Home Assistant.

### Manual

Copy `custom_components/vehicle/` into your `config/custom_components/` directory and restart.

## Configuration

### Add a vehicle

**Settings → Devices & Services → Add Integration → Vehicle**

| Option | Description |
|--------|-------------|
| Name | Vehicle name (must be unique) |
| Drive type | Petrol, diesel, hybrid or electric. Decides whether fuel and/or charge logging and statistics are available |
| Odometer entity | Optional. Any numeric sensor/number in km or mi. Used whenever it has a valid value, otherwise the manual odometer is used |
| Warn within (days / km) | An item counts as *due soon* when this close to its limit |

### Add service items

Open the vehicle entry and choose **Add service item**:

- **Repeat every (days)** and/or **Repeat every (km)** — at least one is required.
- **Last done on / Odometer at last service** — baseline for the first due date. The date defaults to today. If you leave the odometer empty, tracking of the km interval starts at the odometer when first seen.

## Entities

Per vehicle:

| Entity | Description |
|--------|-------------|
| `sensor.<vehicle>_odometer` | Odometer in km. Attributes: `source` (`sensor`/`manual`), `recent_log` |
| `sensor.<vehicle>_fuel_price` | Price per liter of the latest refuel (not for electric); history/trends via HA statistics |
| `sensor.<vehicle>_energy_price` | Price per kWh of the latest charge (hybrid/electric) |
| `sensor.<vehicle>_fuel_consumption` | Average L/100 km (not for electric). Attribute `recent` |
| `sensor.<vehicle>_energy_consumption` | Average kWh/100 km (hybrid/electric). Attribute `recent` |
| `sensor.<vehicle>_cost_per_km` | Fuel + charge cost per km |
| `sensor.<vehicle>_cost_this_month` | Fuel + charge cost in the current month |

Per service item:

| Entity | Description |
|--------|-------------|
| `sensor.<item>` | Status: `ok`, `due_soon`, `overdue`, `unknown`. Attributes with last/next due, days and km remaining |
| `sensor.<item>_days_remaining` | Only if a day interval is set; negative when overdue |
| `sensor.<item>_km_remaining` | Only if a km interval is set; negative when overdue |
| `binary_sensor.<item>_overdue` | `on` when overdue |
| `button.<item>_complete` | Records the service as done today at the current odometer |

Statistics notes: no full tank or full battery is assumed. Consumption over a span of entries is everything added after the first entry divided by the distance since it, so it becomes more accurate with more entries (`recent` covers the last 3 intervals). Entries need an `odometer` value to be included in consumption and cost-per-km.

## Services

| Service | Description |
|---------|-------------|
| `vehicle.set_odometer` | Set the manual odometer. Lower values are rejected unless `allow_decrease: true` |
| `vehicle.add_fuel` | Log a refuel: `liters`, `price_per_liter` (or `total_cost`, from which the price is derived), `odometer`, `date` |
| `vehicle.add_charge` | Log a charge: `kwh`, `price_per_kwh` (or `total_cost`), `odometer`, `date` |
| `vehicle.complete_service` | Record a service item as done: `odometer`, `date`, `cost`, `receipt` |
| `vehicle.upload_receipt` | Store a file uploaded via HA (`/api/file_upload`) and return a `receipt` id (response service) |
| `vehicle.scan_receipt` | Read values from a receipt with an AI task entity (response service, nothing is saved) |
| `vehicle.attach_receipt` | Attach a `receipt` to an existing log entry (`log_entry_id`) or to the latest completion of a service item |
| `vehicle.delete_log_entry` | Delete a fuel/charge entry (`log_entry_id`, see `recent_log` on the odometer sensor) with its receipt |

`add_fuel`, `add_charge` and `complete_service` also accept an optional `receipt` id.

All services take an `entity_id`; any entity of the vehicle (or service item for `complete_service`) works.

```yaml
action: vehicle.add_fuel
data:
  entity_id: sensor.golf_odometer
  liters: 42.3
  price_per_liter: 1.683
  odometer: 45210
```

## Lovelace card

The card is registered automatically.

```yaml
type: custom:vehicle-card
entity: sensor.golf_odometer
```

| Option | Default | Description |
|--------|---------|-------------|
| `entity` | — | Any sensor of the vehicle, e.g. the odometer |
| `title` | vehicle name | Card title |
| `show_stats` | `true` | Consumption and cost row |
| `show_log` | `true` | Recent refuels/charges |

### `vehicle-log-card` — add fuel / charge

A small form to log a refuel or charge (date, liters or kWh, price per unit, optional odometer). It shows the total, hints the last price and current odometer, and calls `vehicle.add_fuel` / `vehicle.add_charge`. Hybrids get a Fuel/Charge switch.

```yaml
type: custom:vehicle-log-card
entity: sensor.golf_odometer
```

| Option | Default | Description |
|--------|---------|-------------|
| `entity` | — | Any sensor of the vehicle |
| `title` | auto | Card title |

### Receipts and invoices

- In `vehicle-log-card` use **Receipt** to take a photo or pick a file; it is attached when you press **Add**. On a service item in `vehicle-card` use the document-plus button to mark it done together with an invoice.
- Photos are shrunk in the browser before upload. JPEG, PNG, WebP and PDF up to 15 MB are accepted.
- Files are stored in `config/.storage/vehicle_receipts/` (included in HA backups) and are only served to logged-in users at `/api/vehicle/receipt/<id>`. They are not reachable via `/local`. Uploads that are never attached are deleted after 24 hours; deleting a log entry, service item or vehicle deletes its files.
- **Scan with AI** appears when an `ai_task` entity exists. It sends the image to the AI provider you configured in Home Assistant (so it leaves your network if that provider is a cloud service), then fills the form for you to check. Values are never saved without your confirmation. With several AI task entities, set a preferred one in Home Assistant, or pass `ai_task_entity_id` to `vehicle.scan_receipt`.

### `vehicle-card` details

It lists service items sorted by urgency with a button to mark them done. For a single value use e.g. a tile or entity card on `sensor.oil_change_km_remaining`.

## Automation example

```yaml
automation:
  - alias: "Vehicle service overdue"
    triggers:
      - trigger: event
        event_type: vehicle_service_overdue
    actions:
      - action: notify.mobile_app
        data:
          title: "{{ trigger.event.data.vehicle }}"
          message: "{{ trigger.event.data.service }} is overdue."
```

The first refresh after a restart only records which items are already overdue, so you are not notified again after every restart.

## Development

### Local test instance

Needs Docker. Starts Home Assistant with the integration mounted, then creates a user (`dev` / `dev`) and two demo vehicles (a petrol car with fuel log and a linked-odometer EV with charges):

```bash
docker compose -f dev/docker-compose.yml up -d
```

```bash
python3 dev/seed.py
```

The seed also adds a **fake AI task provider** (`dev/config/custom_components/fake_ai_task`) that returns canned values instead of reading the image, so you can try *Scan with AI* without an AI account. It is for development only.

Open <http://localhost:8123/dashboard-vehicle>. After code changes restart with `docker compose -f dev/docker-compose.yml restart`. Reset everything by stopping the container and deleting `dev/config/.storage` plus the other generated files in `dev/config` (everything except `configuration.yaml` and `dashboards/`).

### Tests and lint

```bash
pip install pytest-homeassistant-custom-component home-assistant-frontend ruff
ruff check .
pytest
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs-url]: https://hacs.xyz
[license-badge]: https://img.shields.io/github/license/Kogoro/ha-vehicle
[license-url]: https://github.com/Kogoro/ha-vehicle/blob/main/LICENSE
