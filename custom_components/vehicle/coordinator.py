"""DataUpdateCoordinator for the Vehicle integration."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfLength
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import DistanceConverter

from . import calc
from .calc import KIND_CHARGE, KIND_FUEL, ServiceInfo
from .const import (
    ACTIVITY_SIZE,
    CONF_DESCRIPTION,
    CONF_FUEL_TYPE,
    CONF_ICON,
    CONF_INTERVAL_DAYS,
    CONF_INTERVAL_KM,
    CONF_LAST_DATE,
    CONF_LAST_ODOMETER,
    CONF_ODOMETER_ENTITY,
    CONF_WARN_DAYS,
    CONF_WARN_KM,
    DEFAULT_WARN_DAYS,
    DEFAULT_WARN_KM,
    DOMAIN,
    EVENT_SERVICE_COMPLETED,
    EVENT_SERVICE_DUE_SOON,
    EVENT_SERVICE_OVERDUE,
    SUBENTRY_TYPE_SERVICE,
    FuelType,
    ServiceStatus,
)
from .store import VehicleStore

_LOGGER = logging.getLogger(__name__)

type VehicleConfigEntry = ConfigEntry[VehicleCoordinator]


@dataclass
class ServiceItemData:
    """Computed state of one service item."""

    subentry_id: str
    name: str
    icon: str | None
    description: str | None
    interval_days: int | None
    interval_km: int | None
    last_date: datetime.date | None
    last_odometer: float | None
    info: ServiceInfo
    history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class VehicleData:
    """All computed data of one vehicle."""

    name: str
    fuel_type: FuelType
    odometer: float | None
    odometer_source: str
    items: dict[str, ServiceItemData] = field(default_factory=dict)
    activity: list[dict[str, Any]] = field(default_factory=list)
    fuel_consumption: float | None = None
    fuel_consumption_latest: float | None = None
    energy_consumption: float | None = None
    energy_consumption_latest: float | None = None
    fuel_price: float | None = None
    energy_price: float | None = None
    cost_per_km: float | None = None
    monthly_cost: float = 0.0
    monthly_fuel_cost: float = 0.0
    monthly_energy_cost: float = 0.0
    monthly_service_cost: float = 0.0


class VehicleCoordinator(DataUpdateCoordinator[VehicleData]):
    """Computes the state of a vehicle from config, store and linked sensors."""

    config_entry: VehicleConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: VehicleConfigEntry,
        store: VehicleStore,
    ) -> None:
        """Initialize the coordinator."""
        self.store = store
        self._overdue: set[str] | None = None
        self._due_soon: set[str] | None = None
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=datetime.timedelta(minutes=15),
        )

    @property
    def fuel_type(self) -> FuelType:
        """Return the drive type of the vehicle."""
        return FuelType(self.config_entry.data[CONF_FUEL_TYPE])

    def start_tracking(self) -> None:
        """Refresh whenever the linked odometer entity changes."""
        entity_id = self.config_entry.data.get(CONF_ODOMETER_ENTITY)
        if not entity_id:
            return

        async def _changed(_: Event[EventStateChangedData]) -> None:
            await self.async_request_refresh()

        self.config_entry.async_on_unload(
            async_track_state_change_event(self.hass, [entity_id], _changed)
        )

    def _read_linked_odometer(self) -> float | None:
        """Read the linked odometer sensor in km, if available."""
        entity_id = self.config_entry.data.get(CONF_ODOMETER_ENTITY)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            value = float(state.state)
        except ValueError:
            return None
        unit = state.attributes.get("unit_of_measurement")
        if unit and unit != UnitOfLength.KILOMETERS:
            try:
                value = DistanceConverter.convert(value, unit, UnitOfLength.KILOMETERS)
            except Exception:  # noqa: BLE001
                _LOGGER.warning("Unsupported odometer unit %s on %s", unit, entity_id)
                return None
        return round(value, 1)

    @property
    def odometer(self) -> tuple[float | None, str]:
        """Return the current odometer and where it came from."""
        linked = self._read_linked_odometer()
        if linked is not None:
            return linked, "sensor"
        manual = self.store.vehicle(self.config_entry.entry_id)["odometer"]
        return manual, "manual"

    def _item_data(
        self,
        subentry_id: str,
        data: dict[str, Any],
        title: str,
        today: datetime.date,
        odometer: float | None,
    ) -> ServiceItemData:
        record = self.store.service(subentry_id)
        interval_days = int(data[CONF_INTERVAL_DAYS]) if data.get(CONF_INTERVAL_DAYS) else None
        interval_km = int(data[CONF_INTERVAL_KM]) if data.get(CONF_INTERVAL_KM) else None

        if record["history"]:
            last = record["history"][-1]
            last_date = datetime.date.fromisoformat(last["date"])
            last_odometer = last["odometer"]
        else:
            last_date = (
                datetime.date.fromisoformat(data[CONF_LAST_DATE])
                if data.get(CONF_LAST_DATE)
                else None
            )
            last_odometer = data.get(CONF_LAST_ODOMETER)
            if last_odometer is None and interval_km and odometer is not None:
                self.store.set_baseline_odometer(subentry_id, odometer)
            if last_odometer is None:
                last_odometer = record["baseline_odometer"]

        entry_data = self.config_entry.data
        info = calc.service_info(
            interval_days=interval_days,
            interval_km=interval_km,
            last_date=last_date,
            last_odometer=last_odometer,
            today=today,
            odometer=odometer,
            warn_days=int(entry_data.get(CONF_WARN_DAYS, DEFAULT_WARN_DAYS)),
            warn_km=int(entry_data.get(CONF_WARN_KM, DEFAULT_WARN_KM)),
        )
        return ServiceItemData(
            subentry_id=subentry_id,
            name=title,
            icon=data.get(CONF_ICON),
            description=data.get(CONF_DESCRIPTION),
            interval_days=interval_days,
            interval_km=interval_km,
            last_date=last_date,
            last_odometer=last_odometer,
            info=info,
            history=list(reversed(record["history"][-5:])),
        )

    async def _async_update_data(self) -> VehicleData:
        entry = self.config_entry
        today = dt_util.now().date()
        odometer, source = self.odometer
        record = self.store.vehicle(entry.entry_id)
        log = record["log"]

        items = {
            sub.subentry_id: self._item_data(
                sub.subentry_id, dict(sub.data), sub.title, today, odometer
            )
            for sub in entry.subentries.values()
            if sub.subentry_type == SUBENTRY_TYPE_SERVICE
        }

        fuel_avg, fuel_latest = calc.consumption(log, KIND_FUEL)
        energy_avg, energy_latest = calc.consumption(log, KIND_CHARGE)

        histories = [
            (sub.subentry_id, sub.title, self.store.service(sub.subentry_id)["history"])
            for sub in entry.subentries.values()
            if sub.subentry_type == SUBENTRY_TYPE_SERVICE
        ]
        monthly_fuel, monthly_energy = calc.monthly_cost_by_kind(log, today)

        data = VehicleData(
            name=entry.title,
            fuel_type=self.fuel_type,
            odometer=odometer,
            odometer_source=source,
            items=items,
            activity=calc.build_activity(log, histories, ACTIVITY_SIZE),
            fuel_consumption=fuel_avg,
            fuel_consumption_latest=fuel_latest,
            energy_consumption=energy_avg,
            energy_consumption_latest=energy_latest,
            fuel_price=calc.latest_price(log, KIND_FUEL),
            energy_price=calc.latest_price(log, KIND_CHARGE),
            cost_per_km=calc.cost_per_km(log),
            monthly_cost=calc.monthly_cost(log, today),
            monthly_fuel_cost=monthly_fuel,
            monthly_energy_cost=monthly_energy,
            monthly_service_cost=calc.monthly_service_cost(
                [history for _, _, history in histories], today
            ),
        )
        self._fire_status_events(data)
        return data

    def _fire_status_events(self, data: VehicleData) -> None:
        """Fire events when an item newly becomes overdue or due soon.

        The first refresh after startup only seeds the state, so items that
        were already overdue or due soon do not notify again after a restart.
        """
        overdue = {
            sid
            for sid, item in data.items.items()
            if item.info.status is ServiceStatus.OVERDUE
        }
        due_soon = {
            sid
            for sid, item in data.items.items()
            if item.info.status is ServiceStatus.DUE_SOON
        }
        if self._overdue is not None and self._due_soon is not None:
            for sid in overdue - self._overdue:
                self._fire_status_event(EVENT_SERVICE_OVERDUE, data, sid)
            for sid in due_soon - self._due_soon:
                self._fire_status_event(EVENT_SERVICE_DUE_SOON, data, sid)
        self._overdue = overdue
        self._due_soon = due_soon

    def _fire_status_event(self, event_type: str, data: VehicleData, sid: str) -> None:
        item = data.items[sid]
        self.hass.bus.async_fire(
            event_type,
            {
                "entry_id": self.config_entry.entry_id,
                "vehicle": data.name,
                "subentry_id": sid,
                "service": item.name,
                "days_remaining": item.info.days_remaining,
                "km_remaining": item.info.km_remaining,
            },
        )

    # Actions ------------------------------------------------------------

    async def async_complete_service(
        self,
        subentry_id: str,
        *,
        date: datetime.date | None = None,
        odometer: float | None = None,
        cost: float | None = None,
        receipt: str | None = None,
    ) -> None:
        """Record a completed service item."""
        date = date or dt_util.now().date()
        if odometer is None:
            odometer = self.odometer[0]
        elif odometer > (self.odometer[0] or 0):
            self.store.set_odometer(self.config_entry.entry_id, odometer)
        self.store.record_service(subentry_id, date.isoformat(), odometer, cost, receipt)
        await self.async_refresh()

        item = self.data.items.get(subentry_id) if self.data else None
        self.hass.bus.async_fire(
            EVENT_SERVICE_COMPLETED,
            {
                "entry_id": self.config_entry.entry_id,
                "vehicle": self.config_entry.title,
                "subentry_id": subentry_id,
                "service": item.name if item else None,
                "date": date.isoformat(),
                "odometer": odometer,
                "cost": cost,
                "receipt": receipt,
                "next_due_date": (
                    item.info.next_due_date.isoformat()
                    if item and item.info.next_due_date
                    else None
                ),
                "next_due_odometer": item.info.next_due_odometer if item else None,
            },
        )
