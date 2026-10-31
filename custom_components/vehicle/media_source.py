"""Media source exposing receipts, so AI tasks can read them and the media browser can list them."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import BrowseError, MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SUBENTRY_TYPE_SERVICE
from .receipts import RECEIPT_RE, mime_type, receipt_path

FOLDER_PREFIX = "vehicle/"


async def async_get_media_source(hass: HomeAssistant) -> VehicleMediaSource:
    """Set up the receipt media source."""
    return VehicleMediaSource(hass)


class VehicleMediaSource(MediaSource):
    """``media-source://vehicle`` (browse) and ``.../<receipt id>`` (resolve)."""

    name = "Vehicle receipts"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the media source."""
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a receipt to its file."""
        path = await self.hass.async_add_executor_job(
            receipt_path, self.hass, item.identifier
        )
        if path is None:
            raise Unresolvable(f"Receipt {item.identifier} not found")
        return PlayMedia(
            f"/api/vehicle/receipt/{item.identifier}",
            mime_type(item.identifier),
            path=path,
        )

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse vehicles and their receipts."""
        identifier = item.identifier or ""
        if not identifier:
            return self._root()
        if identifier.startswith(FOLDER_PREFIX):
            return self._vehicle_folder(identifier.removeprefix(FOLDER_PREFIX))
        if RECEIPT_RE.match(identifier):
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                for receipt in self._receipts(entry):
                    if receipt["id"] == identifier:
                        return self._file(receipt)
        raise BrowseError(f"Unknown receipt or folder: {identifier}")

    # ------------------------------------------------------------------

    def _store(self):
        return self.hass.data[DOMAIN]["store"]

    def _receipts(self, entry) -> list[dict[str, Any]]:
        """All receipts attached to a vehicle, newest first."""
        store = self._store()
        currency = self.hass.config.currency or ""
        found: list[dict[str, Any]] = []
        for log in store.vehicle(entry.entry_id)["log"]:
            if not log.get("receipt"):
                continue
            unit = "kWh" if log["kind"] == "charge" else "L"
            what = "Charge" if log["kind"] == "charge" else "Refuel"
            found.append(
                {
                    "id": log["receipt"],
                    "date": log["date"],
                    "title": f"{what} {log['amount']:g} {unit}"
                    + (f" · {log['cost']:.2f} {currency}" if log.get("cost") is not None else ""),
                }
            )
        for subentry in entry.subentries.values():
            if subentry.subentry_type != SUBENTRY_TYPE_SERVICE:
                continue
            for record in store.service(subentry.subentry_id)["history"]:
                if record.get("receipt"):
                    found.append(
                        {
                            "id": record["receipt"],
                            "date": record["date"],
                            "title": f"{subentry.title} done"
                            + (f" · {record['cost']:.2f} {currency}" if record.get("cost") is not None else ""),
                        }
                    )
        found.sort(key=lambda r: r["date"], reverse=True)
        return found

    def _file(self, receipt: dict[str, Any]) -> BrowseMediaSource:
        mime = mime_type(receipt["id"])
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=receipt["id"],
            media_class=MediaClass.DOCUMENT if mime == "application/pdf" else MediaClass.IMAGE,
            media_content_type=mime,
            title=f"{receipt['date']} · {receipt['title']}",
            can_play=True,
            can_expand=False,
        )

    def _vehicle_folder(self, entry_id: str) -> BrowseMediaSource:
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise BrowseError(f"Unknown vehicle: {entry_id}")
        folder = BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{FOLDER_PREFIX}{entry_id}",
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=entry.title,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.IMAGE,
        )
        folder.children = [self._file(receipt) for receipt in self._receipts(entry)]
        return folder

    def _root(self) -> BrowseMediaSource:
        root = BrowseMediaSource(
            domain=DOMAIN,
            identifier="",
            media_class=MediaClass.APP,
            media_content_type="",
            title=self.name,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
        )
        children = []
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            count = len(self._receipts(entry))
            folder = self._vehicle_folder(entry.entry_id)
            folder.title = f"{entry.title} ({count})"
            folder.children = None  # listed when the folder is opened
            children.append(folder)
        root.children = children
        return root
