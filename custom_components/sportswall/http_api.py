"""HTTP API so the tablet/TV HTML board can pin a featured game."""

from __future__ import annotations

from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    BOARD_VIEWS,
    DOMAIN,
    STYLE_ARENA,
    STYLE_BROADCAST,
    STYLE_DAYLIGHT,
    STYLE_NIGHT,
    UI_THEMES,
)
from .runtime import SportswallRuntime

_THEMES = {
    STYLE_ARENA,
    STYLE_BROADCAST,
    STYLE_NIGHT,
    STYLE_DAYLIGHT,
} | set(UI_THEMES)

_HTTP_FLAG = "_http_registered"


def async_register_http(hass: HomeAssistant) -> None:
    """Register kiosk endpoints once."""
    hass.data.setdefault(DOMAIN, {})
    if hass.data[DOMAIN].get(_HTTP_FLAG):
        return
    hass.http.register_view(SportswallFeaturedView)
    hass.http.register_view(SportswallThemeView)
    hass.http.register_view(SportswallModeView)
    hass.data[DOMAIN][_HTTP_FLAG] = True


def _runtimes(hass: HomeAssistant) -> list[SportswallRuntime]:
    return [
        runtime
        for runtime in hass.data.get(DOMAIN, {}).values()
        if isinstance(runtime, SportswallRuntime)
    ]


def _runtime_for(hass: HomeAssistant, entry_id: str | None) -> SportswallRuntime | None:
    runtimes = _runtimes(hass)
    if not runtimes:
        return None
    if entry_id:
        for runtime in runtimes:
            if runtime.entry.entry_id == entry_id:
                return runtime
        return None
    return runtimes[0]


class SportswallFeaturedView(HomeAssistantView):
    """GET/POST featured game for the HTML board (LAN kiosk, no HA login)."""

    url = "/api/sportswall/featured"
    name = "api:sportswall:featured"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        entry_id = request.query.get("entry_id")
        runtime = _runtime_for(hass, entry_id)
        if runtime is None:
            return self.json({"error": "not_loaded"}, status_code=404)
        featured = runtime.featured_game
        return self.json(
            {
                "entry_id": runtime.entry.entry_id,
                "pinned_game_id": runtime.pinned_game_id,
                "featured_game_id": featured.id if featured else None,
                "board_view": runtime.board_view,
                "ui_theme": runtime.ui_theme,
                "options": _options_payload(runtime),
            }
        )

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return self.json({"error": "invalid_json"}, status_code=400)
        if not isinstance(body, dict):
            return self.json({"error": "invalid_json"}, status_code=400)
        entry_id = body.get("entry_id") or request.query.get("entry_id")
        runtime = _runtime_for(hass, str(entry_id) if entry_id else None)
        if runtime is None:
            return self.json({"error": "not_loaded"}, status_code=404)
        auto = bool(body.get("auto"))
        game_id = body.get("game_id")
        if isinstance(game_id, str):
            game_id = game_id.strip() or None
        else:
            game_id = None
        try:
            await runtime.async_set_pinned_game(None if auto else game_id)
        except HomeAssistantError as err:
            return self.json({"error": str(err)}, status_code=400)
        featured = runtime.featured_game
        return self.json(
            {
                "ok": True,
                "pinned_game_id": runtime.pinned_game_id,
                "featured_game_id": featured.id if featured else None,
                "options": _options_payload(runtime),
            }
        )


class SportswallThemeView(HomeAssistantView):
    """POST theme for the HTML board (LAN kiosk)."""

    url = "/api/sportswall/theme"
    name = "api:sportswall:theme"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return self.json({"error": "invalid_json"}, status_code=400)
        if not isinstance(body, dict):
            return self.json({"error": "invalid_json"}, status_code=400)
        theme = str(body.get("theme") or "").strip()
        if theme not in _THEMES:
            return self.json(
                {"error": "invalid_theme", "allowed": sorted(_THEMES)},
                status_code=400,
            )
        entry_id = body.get("entry_id") or request.query.get("entry_id")
        runtime = _runtime_for(hass, str(entry_id) if entry_id else None)
        if runtime is None:
            return self.json({"error": "not_loaded"}, status_code=404)
        try:
            await runtime.async_set_ui_theme(theme)
        except HomeAssistantError as err:
            return self.json({"error": str(err)}, status_code=400)
        return self.json({"ok": True, "theme": theme, "ui_theme": runtime.ui_theme})


class SportswallModeView(HomeAssistantView):
    """GET/POST SPA board view (game / multi / fantasy / ambient)."""

    url = "/api/sportswall/mode"
    name = "api:sportswall:mode"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        entry_id = request.query.get("entry_id")
        runtime = _runtime_for(hass, entry_id)
        if runtime is None:
            return self.json({"error": "not_loaded"}, status_code=404)
        return self.json(
            {
                "board_view": runtime.board_view,
                "allowed": sorted(BOARD_VIEWS),
            }
        )

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return self.json({"error": "invalid_json"}, status_code=400)
        if not isinstance(body, dict):
            return self.json({"error": "invalid_json"}, status_code=400)
        view = str(body.get("board_view") or body.get("mode") or "").strip()
        if view not in BOARD_VIEWS:
            return self.json(
                {"error": "invalid_mode", "allowed": sorted(BOARD_VIEWS)},
                status_code=400,
            )
        entry_id = body.get("entry_id") or request.query.get("entry_id")
        runtime = _runtime_for(hass, str(entry_id) if entry_id else None)
        if runtime is None:
            return self.json({"error": "not_loaded"}, status_code=404)
        try:
            await runtime.async_set_board_view(view)
        except HomeAssistantError as err:
            return self.json({"error": str(err)}, status_code=400)
        return self.json({"ok": True, "board_view": runtime.board_view})


def _options_payload(runtime: SportswallRuntime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "id": None,
            "label": "Auto",
            "selected": runtime.pinned_game_id is None,
        }
    ]
    for game in runtime.games:
        rows.append(
            {
                "id": game.id,
                "label": runtime.game_option_label(game),
                "selected": runtime.pinned_game_id == game.id,
                "status": game.status,
                "league": game.league_label,
            }
        )
    return rows
