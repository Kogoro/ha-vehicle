"""Receipt and invoice file storage for the Vehicle integration."""

from __future__ import annotations

import re
import shutil
import time
import uuid
from pathlib import Path

from aiohttp import web
from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

RECEIPT_DIR = (".storage", "vehicle_receipts")
RECEIPT_RE = re.compile(r"^[0-9a-f]{16}\.(jpg|png|webp|pdf)$")
MAX_BYTES = 15 * 1024 * 1024
ORPHAN_MAX_AGE = 24 * 3600

MIME_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "pdf": "application/pdf",
}


def receipt_dir(hass: HomeAssistant) -> Path:
    """Return the private receipt directory."""
    return Path(hass.config.path(*RECEIPT_DIR))


def mime_type(receipt_id: str) -> str:
    """Return the MIME type of a receipt id."""
    return MIME_TYPES[receipt_id.rsplit(".", 1)[1]]


def receipt_path(hass: HomeAssistant, receipt_id: str) -> Path | None:
    """Return the file of a receipt, or None if the id is invalid or missing."""
    if not RECEIPT_RE.match(receipt_id):
        return None
    path = receipt_dir(hass) / receipt_id
    return path if path.is_file() else None


def _extension(head: bytes) -> str | None:
    """Detect the file type from its first bytes."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head.startswith(b"%PDF"):
        return "pdf"
    return None


def _import_upload(hass: HomeAssistant, file_id: str) -> str:
    """Move an uploaded file into the receipt directory (runs in the executor)."""
    try:
        with process_uploaded_file(hass, file_id) as source:
            if source.stat().st_size > MAX_BYTES:
                raise HomeAssistantError("receipt_too_large")
            with source.open("rb") as handle:
                extension = _extension(handle.read(16))
            if extension is None:
                raise HomeAssistantError("receipt_unsupported")
            receipt_id = f"{uuid.uuid4().hex[:16]}.{extension}"
            target = receipt_dir(hass)
            target.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target / receipt_id)
            return receipt_id
    except ValueError as err:
        raise HomeAssistantError("receipt_upload_missing") from err


async def async_import_upload(hass: HomeAssistant, file_id: str) -> str:
    """Store an uploaded file as a receipt and return its id."""
    return await hass.async_add_executor_job(_import_upload, hass, file_id)


def _delete(hass: HomeAssistant, receipt_ids: list[str]) -> None:
    for receipt_id in receipt_ids:
        path = receipt_path(hass, receipt_id)
        if path:
            path.unlink(missing_ok=True)


async def async_delete(hass: HomeAssistant, receipt_ids: list[str]) -> None:
    """Delete receipt files."""
    if receipt_ids:
        await hass.async_add_executor_job(_delete, hass, receipt_ids)


def _cleanup(hass: HomeAssistant, referenced: set[str]) -> int:
    directory = receipt_dir(hass)
    if not directory.is_dir():
        return 0
    removed = 0
    cutoff = time.time() - ORPHAN_MAX_AGE
    for path in directory.iterdir():
        if path.name not in referenced and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


async def async_cleanup_orphans(hass: HomeAssistant, referenced: set[str]) -> int:
    """Delete uploaded receipts that were never attached and are older than a day."""
    return await hass.async_add_executor_job(_cleanup, hass, referenced)


class ReceiptView(HomeAssistantView):
    """Serve receipts to authenticated users only."""

    url = "/api/vehicle/receipt/{receipt_id}"
    name = "api:vehicle:receipt"
    requires_auth = True

    async def get(self, request: web.Request, receipt_id: str) -> web.StreamResponse:
        """Return a receipt file."""
        hass: HomeAssistant = request.app["hass"]
        path = receipt_path(hass, receipt_id)
        if path is None:
            raise web.HTTPNotFound
        return web.FileResponse(
            path,
            headers={
                "Content-Type": mime_type(receipt_id),
                "Content-Disposition": "inline",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, max-age=3600",
            },
        )
