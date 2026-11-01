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
            # completions saved by 0.1.0 have no id yet
            for record in self._data["service"].values():
                for completion in record["history"]:
                    completion.setdefault("id", uuid.uuid4().hex[:8])

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
    def delete_log(self, entry_id: str, log_id: str) -> dict[str, Any] | None:
        """Delete a log entry and return it, or None if it does not exist."""
        log = self.vehicle(entry_id)["log"]
        for entry in log:
            if entry["id"] == log_id:
                log.remove(entry)
                self._save()
                return entry
        return None

    @callback
    def attach_to_log(self, entry_id: str, log_id: str, receipt: str) -> str | None:
        """Attach a receipt to a log entry. Returns the replaced receipt, if any."""
        for entry in self.vehicle(entry_id)["log"]:
            if entry["id"] == log_id:
                old = entry.get("receipt")
                entry["receipt"] = receipt
                self._save()
                return old or ""
        return None

    @callback
    def remove_vehicle(self, entry_id: str) -> list[str]:
        """Delete all data of a vehicle and return its receipt ids."""
        record = self._data["vehicles"].pop(entry_id, None)
        self._save()
        return [e["receipt"] for e in (record or {}).get("log", []) if e.get("receipt")]

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
        self,
        subentry_id: str,
        date: str,
        odometer: float | None,
        cost: float | None = None,
        receipt: str | None = None,
    ) -> None:
        """Record a completed service."""
        record: dict[str, Any] = {
            "id": uuid.uuid4().hex[:8],
            "date": date,
            "odometer": odometer,
        }
        if cost is not None:
            record["cost"] = cost
        if receipt:
            record["receipt"] = receipt
        self.service(subentry_id)["history"].append(record)
        self._save()

    @callback
    def update_service(
        self, subentry_id: str, completion_id: str, changes: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """Change a completion. ``None`` values remove a field. Returns (found, old receipt)."""
        history = self.service(subentry_id)["history"]
        for completion in history:
            if completion["id"] == completion_id:
                old = completion.get("receipt")
                for key, value in changes.items():
                    if value is None:
                        completion.pop(key, None)
                    else:
                        completion[key] = value
                history.sort(key=lambda c: c["date"])
                self._save()
                return True, old
        return False, None

    @callback
    def delete_service(self, subentry_id: str, completion_id: str) -> dict[str, Any] | None:
        """Delete a completion and return it."""
        history = self.service(subentry_id)["history"]
        for completion in history:
            if completion["id"] == completion_id:
                history.remove(completion)
                self._save()
                return completion
        return None

    @callback
    def update_log(
        self, entry_id: str, log_id: str, changes: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Change a fuel/charge entry. Returns (updated entry or None, old receipt)."""
        log = self.vehicle(entry_id)["log"]
        for entry in log:
            if entry["id"] == log_id:
                old = entry.get("receipt")
                for key, value in changes.items():
                    if value is None:
                        entry.pop(key, None)
                    else:
                        entry[key] = value
                log.sort(key=lambda e: e["date"])
                self._save()
                return entry, old
        return None, None

    @callback
    def attach_to_service(self, subentry_id: str, receipt: str) -> str | None:
        """Attach a receipt to the latest completion. Returns the replaced one."""
        history = self.service(subentry_id)["history"]
        if not history:
            return None
        old = history[-1].get("receipt")
        history[-1]["receipt"] = receipt
        self._save()
        return old or ""

    @callback
    def referenced_receipts(self) -> set[str]:
        """Return all receipt ids currently attached to something."""
        found: set[str] = set()
        for vehicle in self._data["vehicles"].values():
            found.update(e["receipt"] for e in vehicle["log"] if e.get("receipt"))
        for service in self._data["service"].values():
            found.update(h["receipt"] for h in service["history"] if h.get("receipt"))
        return found

    @callback
    def prune_services(self, known: set[str]) -> list[str]:
        """Delete history of service items that no longer exist; return their receipts."""
        removed: list[str] = []
        for subentry_id in set(self._data["service"]) - known:
            removed += self.remove_service(subentry_id)
        return removed

    @callback
    def remove_service(self, subentry_id: str) -> list[str]:
        """Delete history of a service item and return its receipt ids."""
        record = self._data["service"].pop(subentry_id, None)
        self._save()
        return [h["receipt"] for h in (record or {}).get("history", []) if h.get("receipt")]
