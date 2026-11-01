"""The German translation covers everything English does, and the cards know both languages."""

import json
import re
from pathlib import Path

COMPONENT = Path(__file__).parent.parent / "custom_components" / "vehicle"


def _leaves(obj, path=()):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _leaves(value, (*path, key))
    else:
        yield ".".join(path), obj


def _load(name):
    return dict(_leaves(json.loads((COMPONENT / name).read_text(encoding="utf-8"))))


def test_german_matches_english() -> None:
    """Same keys, same placeholders, nothing left in English by accident."""
    english, german = _load("strings.json"), _load("translations/de.json")
    assert set(english) == set(german), sorted(set(english) ^ set(german))
    for key, text in english.items():
        assert set(re.findall(r"\{\w+\}", text)) == set(re.findall(r"\{\w+\}", german[key])), key
    # words that are the same in both languages are fine, but most strings must differ
    same = [k for k in english if english[k] == german[k] and len(english[k]) > 12]
    assert not same, same


def test_english_file_mirrors_strings() -> None:
    """translations/en.json is the shipped copy of strings.json."""
    assert _load("strings.json") == _load("translations/en.json")


def test_card_translations_complete() -> None:
    """Every English card string has a German one, with the same placeholders."""
    source = (COMPONENT / "www" / "vehicle-cards.js").read_text(encoding="utf-8")

    def table(language: str) -> dict[str, str]:
        start = source.index(f"\n  {language}: {{")
        end = source.index("\n  },", start)
        block = source[start:end]
        return {m.group(1).strip('"'): m.group(2) for m in re.finditer(r'("?[\w.]+"?):\s*"((?:[^"\\]|\\.)*)"', block)}

    english, german = table("en"), table("de")
    assert len(english) > 100
    assert set(english) == set(german), sorted(set(english) ^ set(german))
    for key, text in english.items():
        assert set(re.findall(r"\{\w+\}", text)) == set(re.findall(r"\{\w+\}", german[key])), key


async def test_german_strings_are_loaded(hass) -> None:
    """Home Assistant picks up translations/de.json for entities, services and the setup flow."""
    from homeassistant.helpers.translation import async_get_translations

    from .test_vehicle import _setup

    await _setup(hass)
    entity = await async_get_translations(hass, "de", "entity", ["vehicle"])
    assert entity["component.vehicle.entity.sensor.odometer.name"] == "Kilometerstand"
    services = await async_get_translations(hass, "de", "services", ["vehicle"])
    assert services["component.vehicle.services.update_activity.name"] == "Aktivität ändern"
    flow = await async_get_translations(hass, "de", "config", ["vehicle"])
    assert flow["component.vehicle.config.step.user.title"] == "Fahrzeug hinzufügen"
