"""Pure calculation helpers (no Home Assistant dependencies)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from .const import ServiceStatus

KIND_FUEL = "fuel"
KIND_CHARGE = "charge"


@dataclass
class ServiceInfo:
    """Computed state of one service item."""

    status: ServiceStatus
    next_due_date: datetime.date | None
    days_remaining: int | None
    next_due_odometer: float | None
    km_remaining: float | None


def service_info(
    *,
    interval_days: int | None,
    interval_km: int | None,
    last_date: datetime.date | None,
    last_odometer: float | None,
    today: datetime.date,
    odometer: float | None,
    warn_days: int,
    warn_km: int,
) -> ServiceInfo:
    """Compute due dates and status for a service item (date OR mileage)."""
    next_due_date = None
    days_remaining = None
    if interval_days and last_date:
        next_due_date = last_date + datetime.timedelta(days=interval_days)
        days_remaining = (next_due_date - today).days

    next_due_odometer = None
    km_remaining = None
    if interval_km and last_odometer is not None:
        next_due_odometer = last_odometer + interval_km
        if odometer is not None:
            km_remaining = round(next_due_odometer - odometer, 1)

    if days_remaining is None and km_remaining is None:
        status = ServiceStatus.UNKNOWN
    elif (days_remaining is not None and days_remaining < 0) or (
        km_remaining is not None and km_remaining < 0
    ):
        status = ServiceStatus.OVERDUE
    elif (days_remaining is not None and days_remaining <= warn_days) or (
        km_remaining is not None and km_remaining <= warn_km
    ):
        status = ServiceStatus.DUE_SOON
    else:
        status = ServiceStatus.OK

    return ServiceInfo(
        status=status,
        next_due_date=next_due_date,
        days_remaining=days_remaining,
        next_due_odometer=next_due_odometer,
        km_remaining=km_remaining,
    )


def _with_odometer(entries: list[dict[str, Any]], kind: str | None = None) -> list:
    """Return entries that have an odometer value, sorted by odometer."""
    result = [
        e
        for e in entries
        if e.get("odometer") is not None and (kind is None or e["kind"] == kind)
    ]
    result.sort(key=lambda e: (e["odometer"], e["date"]))
    return result


def consumption(
    entries: list[dict[str, Any]], kind: str
) -> tuple[float | None, float | None]:
    """Return (average, latest) consumption per 100 km for a log kind.

    Uses the "full tank to full tank" method: only entries flagged ``full``
    delimit a segment, and everything added in between counts towards it.
    Charge entries are always treated as full.
    """
    rows = _with_odometer(entries, kind)
    anchors = [e for e in rows if e.get("full", True)]
    if len(anchors) < 2:
        return None, None

    def segment(first: dict[str, Any], last: dict[str, Any]) -> float | None:
        distance = last["odometer"] - first["odometer"]
        if distance <= 0:
            return None
        amount = sum(
            e["amount"] for e in rows if first["odometer"] < e["odometer"] <= last["odometer"]
        )
        return round(amount / distance * 100, 2)

    average = segment(anchors[0], anchors[-1])
    latest = segment(anchors[-2], anchors[-1])
    return average, latest


def cost_per_km(entries: list[dict[str, Any]]) -> float | None:
    """Return the overall cost per km across fuel and charge entries."""
    rows = _with_odometer(entries)
    if len(rows) < 2:
        return None
    distance = rows[-1]["odometer"] - rows[0]["odometer"]
    if distance <= 0:
        return None
    total = sum(
        e.get("cost") or 0
        for e in rows
        if e["odometer"] > rows[0]["odometer"]
    )
    if total <= 0:
        return None
    return round(total / distance, 4)


def monthly_cost(entries: list[dict[str, Any]], today: datetime.date) -> float:
    """Return the sum of costs logged in the month of ``today``."""
    total = 0.0
    for e in entries:
        date = datetime.date.fromisoformat(e["date"])
        if date.year == today.year and date.month == today.month:
            total += e.get("cost") or 0
    return round(total, 2)
