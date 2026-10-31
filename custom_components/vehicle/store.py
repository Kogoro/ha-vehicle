"""Persistent storage for the Vehicle integration."""

from __future__ import annotations

import uuid
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


class VehicleStore:
    """Stores odometer readings, fuel/charge logs and service history."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store."""
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, dict[str, Any]] = {"vehicles": {}, "service": {}}

    async def async_load(self) -> None:
        """Load data from disk."""
        raw = await self._store.async_load()
        if raw:
            self._data = {
                "vehicles": raw.get("vehicles", {}),
                "service": raw.get("service", {}),
            }

    @callback
    def _save(self) -> None:
        self._store.async_delay_save(lambda: self._data, 10)

    # Vehicles -----------------------------------------------------------

    @callback
    def vehicle(self, entry_id: str) -> dict[str, Any]:
        """Return (and create) the record of a vehicle."""
        return self._data["vehicles"].setdefault(
            entry_id, {"odometer": None, "log": []}
        )

    @callback
    def set_odometer(
        self, entry_id: str, value: float, *, allow_decrease: bool = False
    ) -> bool:
        """Store a manual odometer value. Returns False if it was rejected."""
        record = self.vehicle(entry_id)
        current = record["odometer"]
        if current is not None and value < current and not allow_decrease:
            return False
        record["odometer"] = value
        self._save()
        return True

    @callback
    def add_log(self, entry_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        """Append a fuel/charge log entry and raise the odometer if needed."""
        record = self.vehicle(entry_id)
        entry = {"id": uuid.uuid4().hex[:8], **entry}
        record["log"].append(entry)
        record["log"].sort(key=lambda e: e["date"])
        odometer = entry.get("odometer")
        if odometer is not None and (
            record["odometer"] is None or odometer > record["odometer"]
        ):
            record["odometer"] = odometer
        self._save()
        return entry

    @callback
    def remove_vehicle(self, entry_id: str) -> None:
        """Delete all data of a vehicle."""
        self._data["vehicles"].pop(entry_id, None)
        self._save()

    # Service items ------------------------------------------------------

    @callback
    def service(self, subentry_id: str) -> dict[str, Any]:
        """Return (and create) the record of a service item."""
        return self._data["service"].setdefault(
            subentry_id, {"baseline_odometer": None, "history": []}
        )

    @callback
    def set_baseline_odometer(self, subentry_id: str, odometer: float) -> None:
        """Remember the odometer at which tracking of an item started."""
        record = self.service(subentry_id)
        if record["baseline_odometer"] is None:
            record["baseline_odometer"] = odometer
            self._save()

    @callback
    def record_service(
        self, subentry_id: str, date: str, odometer: float | None
    ) -> None:
        """Record a completed service."""
        self.service(subentry_id)["history"].append(
            {"date": date, "odometer": odometer}
        )
        self._save()

    @callback
    def prune_services(self, known: set[str]) -> None:
        """Delete history of service items that no longer exist."""
        for subentry_id in set(self._data["service"]) - known:
            self.remove_service(subentry_id)

    @callback
    def remove_service(self, subentry_id: str) -> None:
        """Delete history of a service item."""
        self._data["service"].pop(subentry_id, None)
        self._save()
