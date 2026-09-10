"""Shared runtime: scoreboard polling plus TV image Cast."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.network import get_url

from .board import build_board
from .board_image import write_board_png
from .client import SportsClient
from .const import (
    BOARD_PNG_NAME,
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
    CONF_TV_PLAYER,
    CONF_TV_POWER,
    CONF_UNITS,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_LEAGUES,
    DEFAULT_QUIET_ENABLED,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DEFAULT_SCOPE,
    DEFAULT_SHOW_LOGOS,
    DEFAULT_THEME,
    DEFAULT_TIME_FORMAT,
    DEFAULT_UNITS,
    DISPLAY_LIVE,
    THEME_HA,
    TV_CAST_SOURCES,
    TV_POWER_ON_DELAY,
    VIEW_PATH,
    keepalive_interval,
)
from .dashboard import dashboard_path_for
from .games import Game, games_fingerprint
from .schedule import in_quiet_hours
from .tv import (
    RECAST_REASON,
    TAKEOVER_REASONS,
    cast_source_name,
    should_attempt_cast,
    should_refresh_board,
    should_select_cast,
)

_LOGGER = logging.getLogger(__name__)

OFF_STATES = {"off", "unavailable", "unknown", None}


class SportswallRuntime:
    """Holds today's games and casts the board while the TV is on."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.games: list[Game] = []
        self.next_game: Game | None = None
        self.last_error: str | None = None
        self.tv_enabled = False
        self._live_failed = False
        self.last_cast_reason: str | None = None
        self.last_cast_error: str | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._cast_delay_unsub: CALLBACK_TYPE | None = None
        self._client = SportsClient(async_get_clientsession(hass))
        self._poll_lock = asyncio.Lock()
        self._fingerprint: tuple[tuple[Any, ...], ...] | None = None

    @property
    def tv_power(self) -> str:
        return (self.entry.data.get(CONF_TV_POWER) or "").strip()

    @property
    def tv_player(self) -> str:
        return (self.entry.data.get(CONF_TV_PLAYER) or "").strip()

    @property
    def units(self) -> str:
        return self.entry.data.get(CONF_UNITS, DEFAULT_UNITS)

    @property
    def board_style(self) -> str:
        return self.entry.data.get(CONF_THEME, DEFAULT_THEME)

    @property
    def display_mode(self) -> str:
        return self.entry.data.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE)

    @property
    def time_format(self) -> str:
        return self.entry.data.get(CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT)

    @property
    def show_logos(self) -> bool:
        return bool(self.entry.data.get(CONF_SHOW_LOGOS, DEFAULT_SHOW_LOGOS))

    @property
    def refresh_seconds(self) -> int:
        return int(keepalive_interval(self.entry.data.get(CONF_REFRESH_SECONDS)).total_seconds())

    @property
    def quiet_enabled(self) -> bool:
        return bool(self.entry.data.get(CONF_QUIET_ENABLED, DEFAULT_QUIET_ENABLED))

    @property
    def leagues(self) -> list[str]:
        raw = self.entry.data.get(CONF_LEAGUES, DEFAULT_LEAGUES)
        if isinstance(raw, str):
            raw = [item.strip() for item in raw.split(",") if item.strip()]
        if not isinstance(raw, list) or not raw:
            return list(DEFAULT_LEAGUES)
        return [str(item) for item in raw]

    @property
    def scope(self) -> str:
        return self.entry.data.get(CONF_SCOPE, DEFAULT_SCOPE)

    @property
    def ha_theme(self) -> str:
        return THEME_HA.get(self.board_style, THEME_HA[DEFAULT_THEME])

    @property
    def dashboard_path(self) -> str:
        return dashboard_path_for(self.hass, self.entry)

    @property
    def live(self) -> bool:
        return any(game.is_live for game in self.games)

    @property
    def status(self) -> str:
        if self.last_error and not self.games:
            return "error"
        if self.live:
            return "live"
        if self.games:
            return f"{len(self.games)} games"
        return "idle"

    @property
    def board(self) -> dict[str, Any]:
        return build_board(
            self.games,
            self._local_now(),
            units=self.units,
            theme=self.board_style,
            time_format=self.time_format,
            show_logos=self.show_logos,
            leagues=self.leagues,
            next_game=self.next_game,
        )

    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)

        def _remove() -> None:
            if update in self._listeners:
                self._listeners.remove(update)

        return _remove

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _in_quiet_hours(self) -> bool:
        return in_quiet_hours(
            self._local_now(),
            enabled=self.quiet_enabled,
            start=self.entry.data.get(CONF_QUIET_START, DEFAULT_QUIET_START),
            end=self.entry.data.get(CONF_QUIET_END, DEFAULT_QUIET_END),
        )

    def _local_now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.hass.config.time_zone))
        except (KeyError, ValueError):
            return datetime.now().astimezone()

    async def async_setup(self) -> None:
        if self.tv_power:
            self._unsubs.append(
                async_track_state_change_event(self.hass, [self.tv_power], self._tv_power_changed)
            )
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._keepalive,
                keepalive_interval(self.entry.data.get(CONF_REFRESH_SECONDS)),
            )
        )
        await self.async_refresh()

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._cast_delay_unsub:
            self._cast_delay_unsub()
            self._cast_delay_unsub = None

    async def async_refresh(self) -> bool:
        async with self._poll_lock:
            try:
                games = await self._client.fetch_games(self.leagues, self._local_now(), self.scope)
            except Exception as err:  # noqa: BLE001 — poll must never raise
                self.last_error = str(err)
                _LOGGER.warning("Sports Wall refresh failed: %s", err)
                self._notify()
                return True
            fingerprint = games_fingerprint(games)
            changed = fingerprint != self._fingerprint or self.last_error is not None
            self.games = games
            self.next_game = next((game for game in games if game.status == "pre"), None)
            self.last_error = None
            if not changed:
                return False
            self._fingerprint = fingerprint
            self._notify()
            try:
                await self._write_board_image()
            except OSError as err:
                _LOGGER.warning("Could not write Sports Wall image: %s", err)
            return True

    @callback
    def _tv_power_changed(self, event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or new.state in OFF_STATES:
            return
        self._live_failed = False
        self.hass.add_job(self.async_cast(reason="tv_on", delay=True))

    @callback
    def _keepalive(self, _now: datetime) -> None:
        self.hass.add_job(self._keepalive_task())

    async def _keepalive_task(self) -> None:
        if await self.async_refresh():
            await self.async_cast(reason="keep")

    def _tv_is_on(self) -> bool:
        if not self.tv_power:
            return False
        state = self.hass.states.get(self.tv_power)
        return state is not None and state.state not in OFF_STATES

    def _player_state(self) -> str:
        if not self.tv_player:
            return ""
        state = self.hass.states.get(self.tv_player)
        if state is None:
            return ""
        return str(state.state or "").strip().lower()

    def _tv_source(self) -> str:
        if not self.tv_power:
            return ""
        state = self.hass.states.get(self.tv_power)
        if state is None:
            return ""
        return str(state.attributes.get("source") or "").strip().lower()

    def _player_showing_board(self) -> bool:
        if not self.tv_player:
            return False
        player = self.hass.states.get(self.tv_player)
        if player is None or player.state not in {"playing", "paused"}:
            return False
        content = str(player.attributes.get("media_content_id") or "")
        if BOARD_PNG_NAME in content:
            return True
        app = str(player.attributes.get("app_name") or "").lower()
        if "default media receiver" in app:
            return True
        return self._player_showing_live()

    def _player_showing_live(self) -> bool:
        if not self.tv_player:
            return False
        player = self.hass.states.get(self.tv_player)
        if player is None:
            return False
        app = str(player.attributes.get("app_name") or "").lower()
        return "home assistant" in app or "lovelace" in app

    def _tv_showing_board(self) -> bool:
        if self._tv_source() in TV_CAST_SOURCES:
            return True
        return self._player_showing_board()

    def _should_refresh_board(self) -> bool:
        return should_refresh_board(
            source=self._tv_source(),
            showing_board=self._tv_showing_board(),
        )

    async def async_set_tv_enabled(self, enabled: bool) -> None:
        self.tv_enabled = enabled
        if enabled:
            await self.async_cast(reason="armed")

    def _board_path(self) -> Path:
        return Path(self.hass.config.path("www")) / BOARD_PNG_NAME

    def _json_path(self) -> Path:
        return Path(self.hass.config.path("www", "sportswall", "board.json"))

    def _logo_dir(self) -> Path:
        return Path(self.hass.config.path("www", "sportswall", "logos"))

    def _board_url(self) -> str:
        base = get_url(self.hass, prefer_external=False, allow_internal=True)
        return f"{base.rstrip('/')}/local/{BOARD_PNG_NAME}?t={int(datetime.now().timestamp())}"

    async def _write_board_image(self) -> None:
        payload = self.board

        def _write() -> None:
            write_board_png(
                self._board_path(),
                self.games,
                now=self._local_now(),
                units=self.units,
                style=self.board_style,
                time_format=self.time_format,
                show_logos=self.show_logos,
                leagues=self.leagues,
                next_game=self.next_game,
                logo_dir=self._logo_dir(),
            )
            path = self._json_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        await self.hass.async_add_executor_job(_write)

    async def _select_cast_source(self, reason: str) -> None:
        if not self.tv_power or not should_select_cast(reason):
            return
        state = self.hass.states.get(self.tv_power)
        if state is None:
            return
        source = cast_source_name(state.attributes.get("source_list"))
        if source is None:
            _LOGGER.debug("Skip select_source; %s has no Cast input", self.tv_power)
            return
        await self.hass.services.async_call(
            "media_player",
            "select_source",
            {"entity_id": self.tv_power, "source": source},
            blocking=False,
        )
        await asyncio.sleep(1.5)

    async def _play_board_image(self) -> None:
        await self.hass.services.async_call(
            "media_player",
            "play_media",
            {
                "entity_id": self.tv_player,
                "media_content_id": self._board_url(),
                "media_content_type": "image/png",
            },
            blocking=False,
        )

    async def _cast_live_view(self) -> None:
        await self.hass.services.async_call(
            "cast",
            "show_lovelace_view",
            {
                "entity_id": self.tv_player,
                "dashboard_path": self.dashboard_path,
                "view_path": VIEW_PATH,
            },
            blocking=False,
        )

    async def async_cast(self, reason: str, delay: bool = False) -> None:
        """Show the board on the Chromecast."""
        if not self.tv_player:
            return
        if reason != "recast" and not self.tv_enabled:
            return
        if reason != "armed" and not self._tv_is_on():
            return
        if not should_attempt_cast(
            reason=reason,
            power_on=self._tv_is_on(),
            player_state=self._player_state(),
        ):
            _LOGGER.debug("Skip Sports Wall cast (%s); TV or Cast is off", reason)
            return
        if reason != RECAST_REASON and self._in_quiet_hours():
            _LOGGER.debug("Skip Sports Wall cast (%s); quiet hours", reason)
            return
        if reason not in TAKEOVER_REASONS and not self._should_refresh_board():
            _LOGGER.debug("Skip Sports Wall cast (%s); TV is on another source", reason)
            return
        self.last_cast_reason = reason
        self.last_cast_error = None

        if delay:
            if self._cast_delay_unsub:
                self._cast_delay_unsub()

            @callback
            def _go(_now: datetime) -> None:
                self._cast_delay_unsub = None
                self.hass.add_job(self.async_cast(reason="tv_on"))

            self._cast_delay_unsub = async_call_later(
                self.hass, TV_POWER_ON_DELAY.total_seconds(), _go
            )
            return

        try:
            await self._write_board_image()
            await self._select_cast_source(reason)
            use_live = self.display_mode == DISPLAY_LIVE and not self._live_failed
            if use_live:
                if reason in {"keep", "games"} and self._player_showing_live():
                    return
                await self._cast_live_view()
                if reason in TAKEOVER_REASONS:
                    await asyncio.sleep(8)
                    if not self._player_showing_live():
                        _LOGGER.warning(
                            "Live Home Assistant Cast did not connect on %s; "
                            "showing the board image instead",
                            self.tv_player,
                        )
                        self._live_failed = True
                        await self._play_board_image()
                return
            await self._play_board_image()
        except HomeAssistantError as err:
            self.last_cast_error = str(err)
            _LOGGER.warning("Cast to %s failed (%s): %s", self.tv_player, reason, err)
        except OSError as err:
            self.last_cast_error = str(err)
            _LOGGER.warning("Could not write Sports Wall image (%s): %s", reason, err)
