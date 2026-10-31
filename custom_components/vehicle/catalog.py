"""Catalog of common service items for the import action."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).parent / "service_catalog.json"


def _load() -> dict[str, Any]:
    with CATALOG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


async def load_catalog() -> dict[str, Any]:
    """Load the catalog from disk without blocking the event loop."""
    return await asyncio.to_thread(_load)


def _localized(value: dict[str, str], lang: str) -> str:
    return value.get(lang, value["en"])


def _item(category: dict[str, Any], item: dict[str, Any], lang: str) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": _localized(item["name"], lang),
        "description": _localized(item["description"], lang),
        "icon": item["icon"],
        "interval_days": item["interval_days"],
        "interval_km": item["interval_km"],
        "category_id": category["id"],
    }


async def get_categories(fuel_type: str, lang: str = "en") -> list[dict[str, str]]:
    """Return the categories that have at least one item for this drive type."""
    catalog = await load_catalog()
    return [
        {"id": cat["id"], "name": _localized(cat["name"], lang), "icon": cat["icon"]}
        for cat in catalog["categories"]
        if any(fuel_type in item["applies_to"] for item in cat["items"])
    ]


async def get_items(
    category_ids: list[str], fuel_type: str, lang: str = "en"
) -> list[dict[str, Any]]:
    """Return the items of the selected categories that apply to the drive type."""
    catalog = await load_catalog()
    return [
        _item(cat, item, lang)
        for cat in catalog["categories"]
        if cat["id"] in category_ids
        for item in cat["items"]
        if fuel_type in item["applies_to"]
    ]


async def get_item(item_id: str, lang: str = "en") -> dict[str, Any] | None:
    """Look up a single item by id."""
    catalog = await load_catalog()
    for cat in catalog["categories"]:
        for item in cat["items"]:
            if item["id"] == item_id:
                return _item(cat, item, lang)
    return None
