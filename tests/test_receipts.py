"""Tests for receipt upload, attachment, serving and AI scanning."""

import os
import time

import pytest
from aiohttp import FormData
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.setup import async_setup_component

from custom_components.vehicle.const import DOMAIN
from custom_components.vehicle.receipts import async_cleanup_orphans, receipt_dir

from .test_vehicle import _entity, _setup

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def _upload(hass: HomeAssistant, hass_client, content: bytes = PNG) -> str:
    client = await hass_client()
    data = FormData()
    data.add_field("file", content, filename="r.png", content_type="image/png")
    resp = await client.post("/api/file_upload", data=data)
    assert resp.status == 200
    file_id = (await resp.json())["file_id"]
    result = await hass.services.async_call(
        DOMAIN, "upload_receipt", {"file": file_id}, blocking=True, return_response=True
    )
    return result["receipt"]


async def test_upload_attach_serve_delete(hass: HomeAssistant, hass_client) -> None:
    """A receipt is stored privately, attached, served to users and deleted with its entry."""
    await _setup(hass)
    entity = _entity(hass, "sensor", "_odometer")
    receipt = await _upload(hass, hass_client)
    assert receipt.endswith(".png")
    assert (receipt_dir(hass) / receipt).is_file()

    await hass.services.async_call(
        DOMAIN,
        "add_fuel",
        {"entity_id": entity, "liters": 30, "price_per_liter": 1.8, "receipt": receipt},
        blocking=True,
    )
    log = hass.states.get(entity).attributes["activity"]
    assert log[0]["receipt"] == receipt

    client = await hass_client()
    resp = await client.get(f"/api/vehicle/receipt/{receipt}")
    assert resp.status == 200
    assert resp.headers["Content-Type"].startswith("image/png")
    assert (await client.get("/api/vehicle/receipt/0123456789abcdef.png")).status == 404
    assert (await client.get("/api/vehicle/receipt/..%2F..%2Fsecrets.yaml")).status in (400, 404)

    await hass.services.async_call(
        DOMAIN, "delete_log_entry", {"entity_id": entity, "log_entry_id": log[0]["id"]}, blocking=True
    )
    assert hass.states.get(entity).attributes["activity"] == []
    assert not (receipt_dir(hass) / receipt).exists()


async def test_rejects_bad_files_and_unknown_receipts(hass: HomeAssistant, hass_client) -> None:
    """Only real images/PDFs are accepted and receipts must exist."""
    await _setup(hass)
    entity = _entity(hass, "sensor", "_odometer")
    with pytest.raises(ServiceValidationError):
        await _upload(hass, hass_client, b"#!/bin/sh\necho hi\n" + b"\x00" * 32)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "add_fuel",
            {"entity_id": entity, "liters": 5, "price_per_liter": 1.0, "receipt": "0123456789abcdef.png"},
            blocking=True,
        )


async def test_service_completion_with_invoice(hass: HomeAssistant, hass_client) -> None:
    """A completed service can carry cost and invoice, and attach_receipt replaces it."""
    await _setup(hass)
    status = _entity(hass, "sensor", "oil_status")
    first = await _upload(hass, hass_client)
    await hass.services.async_call(
        DOMAIN,
        "complete_service",
        {"entity_id": status, "odometer": 15000, "cost": 289.5, "receipt": first},
        blocking=True,
    )
    history = hass.states.get(status).attributes["history"]
    assert history[0]["cost"] == 289.5 and history[0]["receipt"] == first

    second = await _upload(hass, hass_client)
    await hass.services.async_call(
        DOMAIN, "attach_receipt", {"entity_id": status, "receipt": second}, blocking=True
    )
    assert hass.states.get(status).attributes["history"][0]["receipt"] == second
    assert not (receipt_dir(hass) / first).exists()


async def test_scan_receipt(hass: HomeAssistant, hass_client) -> None:
    """scan_receipt passes the receipt to the AI task and returns cleaned values."""
    await _setup(hass)
    receipt = await _upload(hass, hass_client)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "scan_receipt", {"receipt": receipt, "kind": "fuel"}, blocking=True, return_response=True
        )

    seen: list[dict] = []

    async def fake_generate(call: ServiceCall):
        seen.append(dict(call.data))
        return {"data": {"date": "2026-10-30", "liters": "41.5", "price_per_liter": 1.799,
                         "total_cost": 0, "odometer": None, "bogus": 5}}

    hass.services.async_register("ai_task", "generate_data", fake_generate, supports_response=SupportsResponse.ONLY)
    result = await hass.services.async_call(
        DOMAIN, "scan_receipt", {"receipt": receipt, "kind": "fuel"}, blocking=True, return_response=True
    )
    assert result == {"values": {"date": "2026-10-30", "liters": 41.5, "price_per_liter": 1.799}}
    assert seen[0]["attachments"][0]["media_content_id"] == f"media-source://vehicle/{receipt}"
    assert set(seen[0]["structure"]) == {"date", "liters", "price_per_liter", "total_cost", "odometer"}

    # the media source resolves the receipt to a local file for the AI task
    from homeassistant.components import media_source

    media = await media_source.async_resolve_media(hass, f"media-source://vehicle/{receipt}", None)
    assert media.path == receipt_dir(hass) / receipt and media.mime_type == "image/png"


async def test_orphan_cleanup(hass: HomeAssistant, hass_client) -> None:
    """Old unattached uploads are removed, referenced and fresh ones stay."""
    await _setup(hass)
    entity = _entity(hass, "sensor", "_odometer")
    kept = await _upload(hass, hass_client)
    old = await _upload(hass, hass_client)
    fresh = await _upload(hass, hass_client)
    await hass.services.async_call(
        DOMAIN, "add_fuel", {"entity_id": entity, "liters": 5, "price_per_liter": 1.0, "receipt": kept}, blocking=True
    )
    past = time.time() - 3 * 24 * 3600
    for name in (kept, old):
        os.utime(receipt_dir(hass) / name, (past, past))

    store = hass.data[DOMAIN]["store"]
    assert await async_cleanup_orphans(hass, store.referenced_receipts()) == 1
    assert (receipt_dir(hass) / kept).exists()
    assert (receipt_dir(hass) / fresh).exists()
    assert not (receipt_dir(hass) / old).exists()


async def test_media_browser_lists_receipts(hass: HomeAssistant, hass_client) -> None:
    """The 'Vehicle receipts' media source can be opened: vehicles, then their files."""
    from homeassistant.components import media_source
    from homeassistant.components.media_player import BrowseError

    entry = await _setup(hass)
    entity = _entity(hass, "sensor", "_odometer")
    assert await async_setup_component(hass, "media_source", {})
    first = await _upload(hass, hass_client)
    second = await _upload(hass, hass_client)
    await hass.services.async_call(
        DOMAIN, "add_fuel", {"entity_id": entity, "liters": 41.2, "price_per_liter": 1.759, "date": "2026-10-30", "receipt": first}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN,
        "complete_service",
        {"entity_id": _entity(hass, "sensor", "oil_status"), "cost": 289.5, "date": "2026-10-12", "receipt": second},
        blocking=True,
    )

    root = await media_source.async_browse_media(hass, "media-source://vehicle")
    assert root.title == "Vehicle receipts" and root.can_expand
    assert [c.title for c in root.children] == ["Golf (2)"]

    folder = await media_source.async_browse_media(hass, root.children[0].media_content_id)
    assert [c.title for c in folder.children] == [
        "2026-10-30 · Refuel 41.2 L · 72.47 EUR",
        "2026-10-12 · Oil change done · 289.50 EUR",
    ]
    assert folder.children[0].can_play and folder.children[0].media_content_type == "image/png"

    resolved = await media_source.async_resolve_media(hass, folder.children[0].media_content_id, None)
    assert resolved.url == f"/api/vehicle/receipt/{first}"

    leaf = await media_source.async_browse_media(hass, f"media-source://vehicle/{first}")
    assert leaf.can_play and not leaf.can_expand
    with pytest.raises(BrowseError):
        await media_source.async_browse_media(hass, "media-source://vehicle/vehicle/nope")
    assert entry.title == "Golf"
