"""Create the Cast-safe Sportswall Lovelace dashboard."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .board import DASHBOARD_MARKDOWN
from .const import DASHBOARD_PATH, DOMAIN, THEME_HA, VIEW_PATH

DEFAULT_GAMES_ENTITY = "sensor.sportswall_games"

_LOGGER = logging.getLogger(__name__)

def dashboard_path_for(hass: HomeAssistant, entry: Any) -> str:
    """First config entry keeps /sports-wall; later ones get a suffix."""
    entries = sorted(
        hass.config_entries.async_entries(DOMAIN),
        key=lambda item: item.entry_id,
    )
    if not entries or entries[0].entry_id == entry.entry_id:
        return DASHBOARD_PATH
    return f"{DASHBOARD_PATH}-{entry.entry_id[:8].lower()}"


def games_entity_for(hass: HomeAssistant, entry: Any) -> str:
    from homeassistant.helpers import entity_registry as er

    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_games"
    )
    return entity_id or DEFAULT_GAMES_ENTITY


def _dashboard_config(theme: str, games_entity: str) -> dict[str, Any]:
    return {
        "title": "Sportswall",
        "views": [
            {
                "title": "Board",
                "path": VIEW_PATH,
                "theme": theme,
                "type": "masonry",
                "cards": [
                    {
                        "type": "markdown",
                        "content": DASHBOARD_MARKDOWN.replace(
                            "__GAMES_ENTITY__", games_entity
                        ),
                    }
                ],
            }
        ],
    }


def _lovelace_data(hass: HomeAssistant) -> Any:
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        if LOVELACE_DATA in hass.data:
            return hass.data[LOVELACE_DATA]
    except ImportError:
        pass
    return hass.data.get("lovelace")


def _register_sidebar(hass: HomeAssistant, path: str) -> None:
    from homeassistant.components import frontend

    exists = False
    if hasattr(frontend, "async_panel_exists"):
        exists = frontend.async_panel_exists(hass, path)

    kwargs: dict[str, Any] = {
        "frontend_url_path": path,
        "require_admin": False,
        "sidebar_title": "Sportswall",
        "sidebar_icon": "mdi:scoreboard",
        "config": {"mode": "storage"},
    }
    if exists:
        kwargs["update"] = True

    frontend.async_register_built_in_panel(hass, "lovelace", **kwargs)


async def async_ensure_dashboard(
    hass: HomeAssistant,
    theme: str | None = None,
    path: str | None = None,
    games_entity: str | None = None,
) -> None:
    """Create or refresh a Sportswall storage dashboard."""
    path = path or DASHBOARD_PATH
    games_entity = games_entity or DEFAULT_GAMES_ENTITY
    ll = _lovelace_data(hass)
    dashboards = getattr(ll, "dashboards", None) if ll is not None else None
    if ll is None or dashboards is None:
        _LOGGER.warning(
            "Lovelace is not ready; add a Sportswall dashboard under "
            "Settings → Dashboards, or reload Sports Wall after a restart"
        )
        return

    if path not in dashboards:
        try:
            from homeassistant.components.lovelace.dashboard import (
                DashboardsCollection,
                LovelaceStorage,
            )

            collection = DashboardsCollection(hass)
            await collection.async_load()
            if not any(item.get("url_path") == path for item in collection.async_items()):
                await collection.async_create_item(
                    {
                        "url_path": path,
                        "title": "Sportswall" if path == DASHBOARD_PATH else path,
                        "icon": "mdi:scoreboard",
                        "show_in_sidebar": True,
                        "require_admin": False,
                    }
                )
            item = next(
                item
                for item in collection.async_items()
                if item.get("url_path") == path
            )
            dashboards[path] = LovelaceStorage(hass, item)
        except (HomeAssistantError, ValueError, StopIteration, ImportError) as err:
            _LOGGER.warning("Could not create the %s dashboard: %s", path, err)
            return

    try:
        _register_sidebar(hass, path)
    except (ValueError, TypeError) as err:
        _LOGGER.debug("Sidebar panel already registered: %s", err)

    dash = dashboards[path]
    save = getattr(dash, "async_save", None)
    if save is None:
        return
    try:
        await save(_dashboard_config(theme or THEME_HA["arena"], games_entity))
    except HomeAssistantError as err:
        _LOGGER.warning("Could not save the Sportswall dashboard: %s", err)
        return

    _LOGGER.info("Sportswall dashboard is at /%s/%s", path, VIEW_PATH)


async def async_write_theme(hass: HomeAssistant) -> None:
    """Drop the dark theme into config/themes if that folder is used."""
    theme_dir = hass.config.path("themes")
    theme_path = hass.config.path("themes", "sportswall.yaml")

    def _write() -> None:
        from pathlib import Path

        Path(theme_dir).mkdir(parents=True, exist_ok=True)
        Path(theme_path).write_text(
            """sportswall:
  primary-color: "#ffc448"
  accent-color: "#ff4652"
  primary-background-color: "#070a12"
  secondary-background-color: "#070a12"
  card-background-color: "#121a2c"
  primary-text-color: "#f6f8fc"
  secondary-text-color: "#94a2bc"
  text-primary-color: "#f6f8fc"
  app-header-background-color: "#0a0e1a"
  app-header-text-color: "#f6f8fc"
  ha-card-background: "#121a2c"
  ha-card-border-width: 0px
  ha-card-border-radius: 16px
  ha-card-box-shadow: "none"
  lovelace-background: "#070a12"

sportswall-broadcast:
  primary-color: "#ffd60a"
  accent-color: "#e61c28"
  primary-background-color: "#08080a"
  secondary-background-color: "#08080a"
  card-background-color: "#16161a"
  primary-text-color: "#fafafa"
  secondary-text-color: "#a8a8b0"
  text-primary-color: "#fafafa"
  app-header-background-color: "#0c0c0e"
  app-header-text-color: "#fafafa"
  ha-card-background: "#16161a"
  ha-card-border-width: 0px
  ha-card-border-radius: 16px
  ha-card-box-shadow: "none"
  lovelace-background: "#08080a"

sportswall-night:
  primary-color: "#8caa78"
  accent-color: "#b44646"
  primary-background-color: "#04060a"
  secondary-background-color: "#04060a"
  card-background-color: "#0c1018"
  primary-text-color: "#a8b4c8"
  secondary-text-color: "#58667c"
  text-primary-color: "#a8b4c8"
  app-header-background-color: "#06080e"
  app-header-text-color: "#a8b4c8"
  ha-card-background: "#0c1018"
  ha-card-border-width: 0px
  ha-card-border-radius: 16px
  ha-card-box-shadow: "none"
  lovelace-background: "#04060a"

sportswall-daylight:
  primary-color: "#c45a1c"
  accent-color: "#c4242a"
  primary-background-color: "#e8ecf2"
  secondary-background-color: "#e8ecf2"
  card-background-color: "#ffffff"
  primary-text-color: "#121824"
  secondary-text-color: "#5a667a"
  text-primary-color: "#121824"
  app-header-background-color: "#f8fafc"
  app-header-text-color: "#121824"
  ha-card-background: "#ffffff"
  ha-card-border-width: 0px
  ha-card-border-radius: 16px
  ha-card-box-shadow: "none"
  lovelace-background: "#e8ecf2"
""",
            encoding="utf-8",
        )

    try:
        await hass.async_add_executor_job(_write)
    except OSError as err:
        _LOGGER.debug("Could not write theme file: %s", err)
        return

    if hass.services.has_service("frontend", "reload_themes"):
        try:
            await hass.services.async_call("frontend", "reload_themes", blocking=False)
        except HomeAssistantError:
            _LOGGER.debug("frontend.reload_themes failed for %s", DOMAIN)
