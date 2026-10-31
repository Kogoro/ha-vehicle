"""Media source exposing receipts, so AI tasks can read them as attachments."""

from __future__ import annotations

from homeassistant.components.media_source import (
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .receipts import mime_type, receipt_path


async def async_get_media_source(hass: HomeAssistant) -> VehicleMediaSource:
    """Set up the receipt media source."""
    return VehicleMediaSource(hass)


class VehicleMediaSource(MediaSource):
    """Resolves ``media-source://vehicle/<receipt id>``."""

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
