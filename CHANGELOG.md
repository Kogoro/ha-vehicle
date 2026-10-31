# Changelog

## 0.1.0

First release.

- **Vehicles**: one config entry and one device per vehicle (petrol, diesel, hybrid, electric), optional odometer sensor link.
- **Service items**: intervals by days, kilometres or both; status, days and km remaining, overdue sensor and a complete button for each item. Import of common items from a catalog (English and German), filtered by drive type.
- **Fuel and charging log** with price per unit, consumption (L/100 km, kWh/100 km), cost per km and monthly costs, including service costs.
- **Receipts and invoices**: photo or PDF upload, private storage, an optional AI scan (Home Assistant AI task) to pre-fill entries, browsable in the Media tab.
- **Events and blueprint**: `vehicle_service_due_soon`, `vehicle_service_overdue`, `vehicle_service_completed` and a notification blueprint.
- **Lovelace cards** with visual editors: `vehicle-info-card` (normal, compact, minimal), `vehicle-activity-card` and `vehicle-entry-card`.
- Tested with Home Assistant 2026.2 and 2026.10.
