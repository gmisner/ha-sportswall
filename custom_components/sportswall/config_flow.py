"""Config flow for Sports Wall."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    ALL_LEAGUES,
    CONF_DISPLAY_MODE,
    CONF_LEAGUES,
    CONF_QUIET_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_REFRESH_SECONDS,
    CONF_SCOPE,
    CONF_SHOW_LOGOS,
    CONF_THEME,
    CONF_TIME_FORMAT,
    CONF_TV_ENABLED,
    CONF_TV_PLAYER,
    CONF_TV_POWER,
    CONF_UNITS,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_LEAGUES,
    DEFAULT_QUIET_ENABLED,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DEFAULT_REFRESH_SECONDS,
    DEFAULT_SCOPE,
    DEFAULT_SHOW_LOGOS,
    DEFAULT_THEME,
    DEFAULT_TIME_FORMAT,
    DEFAULT_UNITS,
    DISPLAY_IMAGE,
    DISPLAY_LIVE,
    DOMAIN,
    LEAGUE_LABELS,
    MAX_REFRESH_SECONDS,
    MIN_REFRESH_SECONDS,
    SCOPE_SLATE,
    SCOPE_TODAY,
    STYLE_ARENA,
    STYLE_BROADCAST,
    STYLE_DAYLIGHT,
    STYLE_NIGHT,
    TIME_12H,
    TIME_24H,
    TIME_FOLLOW_UNITS,
    UNIT_IMPERIAL,
    UNIT_METRIC,
)


def _league_options() -> list[dict[str, str]]:
    return [{"value": key, "label": label} for key, label in LEAGUE_LABELS.items() if key in ALL_LEAGUES]


def _setup_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_LEAGUES,
                default=defaults.get(CONF_LEAGUES, DEFAULT_LEAGUES),
            ): selector({"select": {"options": _league_options(), "multiple": True, "mode": "list"}}),
            vol.Required(
                CONF_TV_ENABLED,
                default=defaults.get(CONF_TV_ENABLED, True),
            ): bool,
            vol.Optional(
                CONF_TV_POWER,
                description={"suggested_value": defaults.get(CONF_TV_POWER, "")},
            ): selector({"entity": {"domain": "media_player"}}),
            vol.Optional(
                CONF_TV_PLAYER,
                description={"suggested_value": defaults.get(CONF_TV_PLAYER, "")},
            ): selector({"entity": {"domain": "media_player"}}),
        }
    )


def _options_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_LEAGUES,
                default=defaults.get(CONF_LEAGUES, DEFAULT_LEAGUES),
            ): selector({"select": {"options": _league_options(), "multiple": True, "mode": "list"}}),
            vol.Required(
                CONF_SCOPE,
                default=defaults.get(CONF_SCOPE, DEFAULT_SCOPE),
            ): selector(
                {
                    "select": {
                        "options": [
                            {"value": SCOPE_TODAY, "label": "Today only"},
                            {"value": SCOPE_SLATE, "label": "Full league slate (week / day board)"},
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
            vol.Required(
                CONF_TV_ENABLED,
                default=defaults.get(CONF_TV_ENABLED, True),
            ): bool,
            vol.Optional(
                CONF_TV_POWER,
                description={"suggested_value": defaults.get(CONF_TV_POWER, "")},
            ): selector({"entity": {"domain": "media_player"}}),
            vol.Optional(
                CONF_TV_PLAYER,
                description={"suggested_value": defaults.get(CONF_TV_PLAYER, "")},
            ): selector({"entity": {"domain": "media_player"}}),
            vol.Required(
                CONF_UNITS,
                default=defaults.get(CONF_UNITS, DEFAULT_UNITS),
            ): selector(
                {
                    "select": {
                        "options": [
                            {"value": UNIT_IMPERIAL, "label": "Imperial (°F, miles)"},
                            {"value": UNIT_METRIC, "label": "Metric (°C, kilometres)"},
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
            vol.Required(
                CONF_DISPLAY_MODE,
                default=defaults.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE),
            ): selector(
                {
                    "select": {
                        "options": [
                            {
                                "value": DISPLAY_IMAGE,
                                "label": "Image (Cast-safe, older Chromecast / smart TV)",
                            },
                            {
                                "value": DISPLAY_LIVE,
                                "label": "Live dashboard (browser / HA Cast)",
                            },
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
            vol.Required(
                CONF_THEME,
                default=defaults.get(CONF_THEME, DEFAULT_THEME),
            ): selector(
                {
                    "select": {
                        "options": [
                            {"value": STYLE_ARENA, "label": "Arena night"},
                            {"value": STYLE_BROADCAST, "label": "Broadcast"},
                            {"value": STYLE_NIGHT, "label": "Night dim"},
                            {"value": STYLE_DAYLIGHT, "label": "Daylight"},
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
            vol.Required(
                CONF_TIME_FORMAT,
                default=defaults.get(CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT),
            ): selector(
                {
                    "select": {
                        "options": [
                            {
                                "value": TIME_FOLLOW_UNITS,
                                "label": "Follow units (12h imperial, 24h metric)",
                            },
                            {"value": TIME_12H, "label": "12-hour"},
                            {"value": TIME_24H, "label": "24-hour"},
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
            vol.Required(
                CONF_SHOW_LOGOS,
                default=defaults.get(CONF_SHOW_LOGOS, DEFAULT_SHOW_LOGOS),
            ): bool,
            vol.Required(
                CONF_REFRESH_SECONDS,
                default=defaults.get(CONF_REFRESH_SECONDS, DEFAULT_REFRESH_SECONDS),
            ): selector(
                {
                    "number": {
                        "min": MIN_REFRESH_SECONDS,
                        "max": MAX_REFRESH_SECONDS,
                        "step": 5,
                        "unit_of_measurement": "s",
                        "mode": "box",
                    }
                }
            ),
            vol.Required(
                CONF_QUIET_ENABLED,
                default=defaults.get(CONF_QUIET_ENABLED, DEFAULT_QUIET_ENABLED),
            ): bool,
            vol.Optional(
                CONF_QUIET_START,
                default=defaults.get(CONF_QUIET_START, DEFAULT_QUIET_START),
            ): selector({"time": {}}),
            vol.Optional(
                CONF_QUIET_END,
                default=defaults.get(CONF_QUIET_END, DEFAULT_QUIET_END),
            ): selector({"time": {}}),
        }
    )


class SportswallConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up Sports Wall."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                unique = f"{','.join(user_input.get(CONF_LEAGUES) or [])}|{user_input.get(CONF_TV_PLAYER) or 'no-tv'}"
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                count = len(self._async_current_entries())
                title = "Sports Wall" if count == 0 else f"Sports Wall ({count + 1})"
                return self.async_create_entry(title=title, data=_store(user_input))

        return self.async_show_form(
            step_id="user",
            data_schema=_setup_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SportswallOptionsFlow:
        return SportswallOptionsFlow(config_entry)


class SportswallOptionsFlow(OptionsFlow):
    """Change leagues and display options later."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=_store(user_input, self._config_entry.data)
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(dict(self._config_entry.data)),
            errors=errors,
        )


def _store(
    user_input: dict[str, Any], existing: dict[str, Any] | None = None
) -> dict[str, Any]:
    data = {
        CONF_UNITS: DEFAULT_UNITS,
        CONF_DISPLAY_MODE: DEFAULT_DISPLAY_MODE,
        CONF_THEME: DEFAULT_THEME,
        CONF_TIME_FORMAT: DEFAULT_TIME_FORMAT,
        CONF_SHOW_LOGOS: DEFAULT_SHOW_LOGOS,
        CONF_QUIET_ENABLED: DEFAULT_QUIET_ENABLED,
        CONF_QUIET_START: DEFAULT_QUIET_START,
        CONF_QUIET_END: DEFAULT_QUIET_END,
        CONF_REFRESH_SECONDS: DEFAULT_REFRESH_SECONDS,
        CONF_LEAGUES: list(DEFAULT_LEAGUES),
        CONF_SCOPE: DEFAULT_SCOPE,
    }
    if existing:
        data.update(existing)
    data.update(user_input)
    leagues = data.get(CONF_LEAGUES) or DEFAULT_LEAGUES
    if isinstance(leagues, str):
        leagues = [item.strip() for item in leagues.split(",") if item.strip()]
    data[CONF_LEAGUES] = [item for item in leagues if item in ALL_LEAGUES] or list(DEFAULT_LEAGUES)
    return data


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if user_input.get(CONF_TV_ENABLED) and not user_input.get(CONF_TV_PLAYER):
        errors[CONF_TV_PLAYER] = "tv_player_required"
    leagues = user_input.get(CONF_LEAGUES) or []
    if not leagues:
        errors[CONF_LEAGUES] = "leagues_required"
    return errors
