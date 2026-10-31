"""Config flow for the Vehicle integration."""

from __future__ import annotations

import datetime
from contextlib import suppress
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    DateSelector,
    EntitySelector,
    EntitySelectorConfig,
    IconSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
from homeassistant.util import dt as dt_util

from .const import (
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
    SUBENTRY_TYPE_IMPORT,
    SUBENTRY_TYPE_SERVICE,
    FuelType,
)


def _number(maximum: float, unit: str, step: float = 1) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=0, max=maximum, step=step, mode=NumberSelectorMode.BOX, unit_of_measurement=unit
        )
    )


def _vehicle_schema(d: dict[str, Any]) -> vol.Schema:
    """Schema for creating or reconfiguring a vehicle."""
    odometer_key = (
        vol.Optional(CONF_ODOMETER_ENTITY, description={"suggested_value": d.get(CONF_ODOMETER_ENTITY)})
    )
    return vol.Schema(
        {
            vol.Required("name", default=d.get("name", "")): TextSelector(TextSelectorConfig()),
            vol.Required(
                CONF_FUEL_TYPE, default=d.get(CONF_FUEL_TYPE, FuelType.PETROL.value)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[t.value for t in FuelType],
                    translation_key="fuel_type",
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            odometer_key: EntitySelector(EntitySelectorConfig(domain=["sensor", "input_number", "number"])),
            vol.Required(
                CONF_WARN_DAYS, default=d.get(CONF_WARN_DAYS, DEFAULT_WARN_DAYS)
            ): _number(365, "d"),
            vol.Required(
                CONF_WARN_KM, default=d.get(CONF_WARN_KM, DEFAULT_WARN_KM)
            ): _number(100000, "km"),
        }
    )


def _entry_data(user_input: dict[str, Any]) -> dict[str, Any]:
    data = {
        CONF_FUEL_TYPE: user_input[CONF_FUEL_TYPE],
        CONF_WARN_DAYS: int(user_input[CONF_WARN_DAYS]),
        CONF_WARN_KM: int(user_input[CONF_WARN_KM]),
    }
    if user_input.get(CONF_ODOMETER_ENTITY):
        data[CONF_ODOMETER_ENTITY] = user_input[CONF_ODOMETER_ENTITY]
    return data


class VehicleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow: one entry per vehicle."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported subentry types."""
        return {
            SUBENTRY_TYPE_SERVICE: ServiceItemSubentryFlow,
            SUBENTRY_TYPE_IMPORT: ImportSubentryFlow,
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a vehicle."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input["name"].strip()
            if not name:
                errors["name"] = "name_required"
            else:
                await self.async_set_unique_id(name.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=name, data=_entry_data(user_input))
        return self.async_show_form(
            step_id="user", data_schema=_vehicle_schema(user_input or {}), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change vehicle settings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input["name"].strip()
            if not name:
                errors["name"] = "name_required"
            else:
                return self.async_update_reload_and_abort(
                    entry, title=name, data=_entry_data(user_input)
                )
        defaults = user_input or {**entry.data, "name": entry.title}
        return self.async_show_form(
            step_id="reconfigure", data_schema=_vehicle_schema(defaults), errors=errors
        )


def _service_schema(d: dict[str, Any], *, creating: bool) -> vol.Schema:
    """Schema for a service item."""
    today = dt_util.now().date().isoformat()

    def optional(key: str, default: Any = None) -> vol.Optional:
        return vol.Optional(key, description={"suggested_value": default})

    return vol.Schema(
        {
            vol.Required("name", default=d.get("name", "")): TextSelector(TextSelectorConfig()),
            optional(CONF_INTERVAL_DAYS, d.get(CONF_INTERVAL_DAYS)): _number(3650, "d"),
            optional(CONF_INTERVAL_KM, d.get(CONF_INTERVAL_KM)): _number(1000000, "km"),
            optional(CONF_LAST_DATE, d.get(CONF_LAST_DATE) or (today if creating else None)): DateSelector(),
            optional(CONF_LAST_ODOMETER, d.get(CONF_LAST_ODOMETER)): _number(10000000, "km", 0.1),
            optional(CONF_DESCRIPTION, d.get(CONF_DESCRIPTION)): TextSelector(
                TextSelectorConfig(multiline=True)
            ),
            optional(CONF_ICON, d.get(CONF_ICON)): IconSelector(),
        }
    )


def _validate_service(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not user_input["name"].strip():
        errors["name"] = "name_required"
    if not user_input.get(CONF_INTERVAL_DAYS) and not user_input.get(CONF_INTERVAL_KM):
        errors["base"] = "interval_required"
    if user_input.get(CONF_LAST_DATE):
        try:
            datetime.date.fromisoformat(user_input[CONF_LAST_DATE])
        except ValueError:
            errors[CONF_LAST_DATE] = "invalid_date"
    return errors


def _service_data(user_input: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key in (CONF_INTERVAL_DAYS, CONF_INTERVAL_KM):
        if user_input.get(key):
            data[key] = int(user_input[key])
    for key in (CONF_LAST_DATE, CONF_DESCRIPTION, CONF_ICON):
        if user_input.get(key):
            data[key] = user_input[key]
    if user_input.get(CONF_LAST_ODOMETER) is not None:
        data[CONF_LAST_ODOMETER] = float(user_input[CONF_LAST_ODOMETER])
    return data


class ServiceItemSubentryFlow(ConfigSubentryFlow):
    """Add or edit a service item."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a service item."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_service(user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input["name"].strip(), data=_service_data(user_input)
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_service_schema(user_input or {}, creating=True),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit a service item."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_service(user_input)
            if not errors:
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=user_input["name"].strip(),
                    data=_service_data(user_input),
                )
        defaults = user_input or {**subentry.data, "name": subentry.title}
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_service_schema(defaults, creating=False),
            errors=errors,
        )


def _days_text(days: int) -> str:
    """Human-friendly interval: 365 -> '1 y', 182 -> '6 mo', 45 -> '45 d'."""
    years = round(days / 365)
    if years >= 1 and abs(days - years * 365) <= 10:
        return f"{years} y"
    months = round(days / 30.44)
    if months >= 2 and abs(days - months * 30.44) <= 4:
        return f"{months} mo"
    return f"{days} d"


def _interval_text(item: dict[str, Any]) -> str:
    parts = []
    if item.get("interval_days"):
        parts.append(_days_text(item["interval_days"]))
    if item.get("interval_km"):
        parts.append(f"{item['interval_km']:,} km".replace(",", " "))
    return " / ".join(parts)


class ImportSubentryFlow(ConfigSubentryFlow):
    """Import common service items from the catalog (like ha-task's task import)."""

    def __init__(self) -> None:
        """Initialize the import flow."""
        super().__init__()
        self._categories: list[str] = []
        self._item_ids: list[str] = []
        self._lang: str | None = None

    async def _resolve_lang(self) -> str:
        """Use the requesting user's frontend language, then the system language, then English."""
        if self._lang is not None:
            return self._lang
        lang: str | None = None
        with suppress(Exception):
            from homeassistant.helpers.http import current_request

            if (request := current_request.get()) is not None and (
                user := request.get("hass_user")
            ) is not None:
                from homeassistant.components.frontend import storage as frontend_store

                store = await frontend_store.async_user_store(self.hass, user.id)
                lang = store.data.get("language", {}).get("language")
        self._lang = (lang or self.hass.config.language or "en").split("-", 1)[0]
        return self._lang

    def _fuel_type(self) -> str:
        return self._get_entry().data[CONF_FUEL_TYPE]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Step 1: choose categories."""
        from .catalog import get_categories

        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("categories"):
                self._categories = user_input["categories"]
                return await self.async_step_select_items()
            errors["categories"] = "no_categories_selected"

        categories = await get_categories(self._fuel_type(), await self._resolve_lang())
        if not categories:
            return self.async_abort(reason="catalog_empty")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("categories"): SelectSelector(
                        SelectSelectorConfig(
                            options=[{"value": c["id"], "label": c["name"]} for c in categories],
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_select_items(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Step 2: choose items."""
        from .catalog import get_items

        items = await get_items(self._categories, self._fuel_type(), await self._resolve_lang())
        if not items:
            return self.async_abort(reason="no_items_found")
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("items"):
                self._item_ids = user_input["items"]
                return await self.async_step_configure()
            errors["items"] = "no_items_selected"

        existing = {sub.title for sub in self._get_entry().subentries.values()}
        options = []
        for item in items:
            label = item["name"]
            if text := _interval_text(item):
                label += f" ({text})"
            if item["name"] in existing:
                label += " \u2022 exists"
            options.append({"value": item["id"], "label": label})
        return self.async_show_form(
            step_id="select_items",
            data_schema=vol.Schema(
                {
                    vol.Required("items"): SelectSelector(
                        SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.LIST)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Step 3: when were these items last done?"""
        if user_input is not None:
            return await self._create(user_input)
        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_LAST_DATE,
                        description={"suggested_value": dt_util.now().date().isoformat()},
                    ): DateSelector()
                }
            ),
        )

    async def _create(self, user_input: dict[str, Any]) -> SubentryFlowResult:
        from .catalog import get_item

        entry = self._get_entry()
        lang = await self._resolve_lang()
        count = 0
        for item_id in self._item_ids:
            item = await get_item(item_id, lang)
            if item is None:
                continue
            data: dict[str, Any] = {CONF_DESCRIPTION: item["description"], CONF_ICON: item["icon"]}
            if item["interval_days"]:
                data[CONF_INTERVAL_DAYS] = item["interval_days"]
            if item["interval_km"]:
                data[CONF_INTERVAL_KM] = item["interval_km"]
            if user_input.get(CONF_LAST_DATE):
                data[CONF_LAST_DATE] = user_input[CONF_LAST_DATE]
            self.hass.config_entries.async_add_subentry(
                entry,
                ConfigSubentry(
                    data=data,
                    subentry_type=SUBENTRY_TYPE_SERVICE,
                    title=item["name"],
                    unique_id=None,
                ),
            )
            count += 1
        return self.async_abort(
            reason="import_success", description_placeholders={"count": str(count)}
        )
