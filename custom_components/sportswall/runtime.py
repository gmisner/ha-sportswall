"""Shared runtime: scoreboard polling plus TV image Cast."""

from __future__ import annotations

import asyncio
import json
import logging
import time
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

from .board import build_board, resolve_featured
from .board_image import write_board_png
from .client import SportsClient
from .const import (
    BOARD_PNG_NAME,
    BOARD_VIEW_LABELS,
    BOARD_VIEWS,
    CONF_BOARD_VIEW,
    CONF_DISPLAY_MODE,
    CONF_FANTASY_ENABLED,
    CONF_FANTASY_ESPN_S2,
    CONF_FANTASY_LEAGUE_ID,
    CONF_FANTASY_SEASON,
    CONF_FANTASY_SWID,
    CONF_FANTASY_TEAM_ID,
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
    CONF_UI_THEME,
    CONF_UNITS,
    DEFAULT_BOARD_VIEW,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_FANTASY_ENABLED,
    DEFAULT_LEAGUES,
    DEFAULT_QUIET_ENABLED,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DEFAULT_SCOPE,
    DEFAULT_SHOW_LOGOS,
    DEFAULT_THEME,
    DEFAULT_TIME_FORMAT,
    DEFAULT_UI_THEME,
    DEFAULT_UNITS,
    DISPLAY_LIVE,
    FEATURED_AUTO,
    THEME_HA,
    TV_CAST_SOURCES,
    TV_POWER_ON_DELAY,
    UI_THEME_TO_STYLE,
    UI_THEMES,
    VIEW_PATH,
    FEATURED_ENRICH_SECONDS,
    LIVE_REFRESH_SECONDS,
    keepalive_interval,
    poll_tick_interval,
)
from .dashboard import dashboard_path_for
from .fantasy_espn import current_fantasy_season
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
        self.pinned_game_id: str | None = None
        self.featured_leaders: list[dict[str, str]] = []
        self.featured_odds: dict[str, str] | None = None
        self.fantasy_players: list[dict[str, str]] = []
        self.fantasy_error: str | None = None
        self._live_failed = False
        self.last_cast_reason: str | None = None
        self.last_cast_error: str | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._cast_delay_unsub: CALLBACK_TYPE | None = None
        self._client = SportsClient(async_get_clientsession(hass))
        self._poll_lock = asyncio.Lock()
        self._fingerprint: tuple[Any, ...] | None = None
        self._last_poll_monotonic: float | None = None
        self._last_enrich_monotonic: float | None = None
        self._last_enrich_game_id: str | None = None

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
    def ui_theme(self) -> str:
        value = str(self.entry.data.get(CONF_UI_THEME) or self.board_style or DEFAULT_UI_THEME)
        return value if value in UI_THEMES else DEFAULT_UI_THEME

    @property
    def board_view(self) -> str:
        value = str(self.entry.data.get(CONF_BOARD_VIEW) or DEFAULT_BOARD_VIEW)
        return value if value in BOARD_VIEWS else DEFAULT_BOARD_VIEW

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
    def fantasy_enabled(self) -> bool:
        return bool(self.entry.data.get(CONF_FANTASY_ENABLED, DEFAULT_FANTASY_ENABLED))

    @property
    def featured_game(self) -> Game | None:
        return resolve_featured(self.games, self.pinned_game_id)

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
            ui_theme=self.ui_theme,
            board_view=self.board_view,
            time_format=self.time_format,
            show_logos=self.show_logos,
            leagues=self.leagues,
            next_game=self.next_game,
            featured_game_id=self.pinned_game_id,
            leaders=self.featured_leaders,
            odds=self.featured_odds,
            fantasy_players=self.fantasy_players,
            fantasy_enabled=self.fantasy_enabled,
            fantasy_error=self.fantasy_error,
        )

    def game_option_label(self, game: Game) -> str:
        away = game.away.abbreviation if game.away else "?"
        home = game.home.abbreviation if game.home else "?"
        if game.is_live:
            status = "LIVE"
        elif game.is_final:
            status = "FINAL"
        else:
            status = "UPCOMING"
        return f"{away} @ {home} · {game.league_label} · {status}"

    def featured_options(self) -> list[str]:
        return ["Auto"] + [self.game_option_label(game) for game in self.games]

    def option_for_game_id(self, game_id: str | None) -> str:
        if not game_id:
            return "Auto"
        for game in self.games:
            if game.id == game_id:
                return self.game_option_label(game)
        return "Auto"

    def game_id_for_option(self, option: str) -> str | None:
        if option.strip().lower() in {FEATURED_AUTO, "auto"}:
            return None
        for game in self.games:
            if self.game_option_label(game) == option:
                return game.id
        return None

    async def async_set_pinned_game(self, game_id: str | None) -> None:
        """Pin a board game as featured, or None for Auto.

        Returns after board.json is updated so the HTML picker stays snappy.
        Leaders/fantasy enrich, PNG, and Cast run in the background.
        """
        if game_id and not any(game.id == game_id for game in self.games):
            raise HomeAssistantError(f"Game {game_id} is not on today's board")
        if self.pinned_game_id == game_id:
            self._notify()
            return
        self.pinned_game_id = game_id
        # Force a fresh enrich for the newly pinned matchup in the follow-up task.
        self._last_enrich_game_id = None
        self._fingerprint = None
        try:
            await self._write_board_json()
        except OSError as err:
            _LOGGER.warning("Could not write Sports Wall board.json: %s", err)
        self._notify()
        self.hass.async_create_task(
            self._async_after_pin(),
            name="sportswall_after_pin",
        )

    async def _async_after_pin(self) -> None:
        """Finish pin work that should not block the kiosk API."""
        try:
            await self._enrich_featured()
            try:
                await self._write_board_json()
            except OSError as err:
                _LOGGER.warning("Could not write Sports Wall board.json: %s", err)
            self._notify()
            try:
                await self._write_board_png()
            except OSError as err:
                _LOGGER.warning("Could not write Sports Wall image: %s", err)
            if self.tv_enabled:
                await self.async_cast(reason="games")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Sports Wall post-pin update failed")

    async def async_set_board_view(self, view: str) -> None:
        """Persist SPA layout: game / multi / fantasy / ambient."""
        if view not in BOARD_VIEWS:
            raise HomeAssistantError(f"Unknown board view: {view}")
        if self.board_view == view:
            self._notify()
            return
        data = dict(self.entry.data)
        data[CONF_BOARD_VIEW] = view
        self.hass.config_entries.async_update_entry(self.entry, data=data)
        self._notify()

    async def async_set_ui_theme(self, theme: str) -> None:
        """Persist SPA chrome theme; map to PNG style when applicable."""
        if theme not in UI_THEMES:
            raise HomeAssistantError(f"Unknown theme: {theme}")
        data = dict(self.entry.data)
        data[CONF_UI_THEME] = theme
        style = UI_THEME_TO_STYLE.get(theme)
        if style:
            data[CONF_THEME] = style
        self.hass.config_entries.async_update_entry(self.entry, data=data)
        self._fingerprint = None
        await self.async_refresh()
        try:
            await self._write_board_image()
        except OSError as err:
            _LOGGER.warning("Could not write Sports Wall image: %s", err)
        self._notify()

    def board_view_options(self) -> list[str]:
        from .const import (
            BOARD_VIEW_AMBIENT,
            BOARD_VIEW_FANTASY,
            BOARD_VIEW_GAME,
            BOARD_VIEW_MULTI,
        )

        order = (
            BOARD_VIEW_GAME,
            BOARD_VIEW_MULTI,
            BOARD_VIEW_FANTASY,
            BOARD_VIEW_AMBIENT,
        )
        return [BOARD_VIEW_LABELS[key] for key in order]

    def board_view_label(self) -> str:
        return BOARD_VIEW_LABELS.get(self.board_view, BOARD_VIEW_LABELS[DEFAULT_BOARD_VIEW])

    def board_view_for_label(self, label: str) -> str | None:
        for key, name in BOARD_VIEW_LABELS.items():
            if name == label or key == label:
                return key
        return None

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
                poll_tick_interval(),
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
            self.games = games
            self.next_game = next((game for game in games if game.status == "pre"), None)
            self.last_error = None
            if self.pinned_game_id and not any(game.id == self.pinned_game_id for game in games):
                self.pinned_game_id = None
            await self._enrich_featured()
            fingerprint = self._board_fingerprint()
            changed = fingerprint != self._fingerprint or self.last_error is not None
            # SPA always needs a fresh board.json; PNG is only for Cast image mode.
            try:
                await self._write_board_json()
            except OSError as err:
                _LOGGER.warning("Could not write Sports Wall board.json: %s", err)
            if changed:
                self._fingerprint = fingerprint
                self._notify()
                try:
                    await self._write_board_png()
                except OSError as err:
                    _LOGGER.warning("Could not write Sports Wall image: %s", err)
                return True
            if self.live:
                self._notify()
            return False

    def _featured_enrich_due(self, game_id: str | None) -> bool:
        if game_id != self._last_enrich_game_id:
            return True
        last = self._last_enrich_monotonic
        if last is None:
            return True
        return (time.monotonic() - last) >= FEATURED_ENRICH_SECONDS

    async def _enrich_featured(self) -> None:
        featured = self.featured_game
        if featured is None:
            self.featured_leaders = []
            self.featured_odds = None
            self.fantasy_players = []
            self.fantasy_error = None
            self._last_enrich_game_id = None
            return
        # Coaches hang off Game objects that are rebuilt every scoreboard poll.
        # Always re-apply from cache so Art'ifacts do not flicker on/off.
        try:
            await self._client.enrich_coaches(featured)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Coach fetch failed: %s", err)
        if not self._featured_enrich_due(featured.id):
            return
        try:
            self.featured_leaders, self.featured_odds = await self._client.fetch_summary_extras(
                featured
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Leaders/odds fetch failed: %s", err)
            self.featured_leaders = []
            self.featured_odds = None
        self.fantasy_players = []
        self.fantasy_error = None
        self._last_enrich_monotonic = time.monotonic()
        self._last_enrich_game_id = featured.id
        if not self.fantasy_enabled:
            return
        league_id = str(self.entry.data.get(CONF_FANTASY_LEAGUE_ID) or "").strip()
        team_id = str(self.entry.data.get(CONF_FANTASY_TEAM_ID) or "").strip()
        espn_s2 = str(self.entry.data.get(CONF_FANTASY_ESPN_S2) or "").strip()
        swid = str(self.entry.data.get(CONF_FANTASY_SWID) or "").strip()
        if not (league_id and team_id and espn_s2 and swid):
            self.fantasy_error = "Fantasy enabled but league/team/cookies are incomplete"
            return
        season_raw = self.entry.data.get(CONF_FANTASY_SEASON)
        season = None
        if season_raw not in (None, ""):
            try:
                season = int(season_raw)
            except (TypeError, ValueError):
                season = current_fantasy_season(self._local_now())
        try:
            self.fantasy_players = await self._client.fetch_fantasy_players(
                featured,
                league_id=league_id,
                team_id=team_id,
                espn_s2=espn_s2,
                swid=swid,
                season=season,
            )
            self.fantasy_error = self._client.fantasy_error
        except Exception as err:  # noqa: BLE001
            self.fantasy_error = str(err)
            _LOGGER.warning("Fantasy roster fetch failed: %s", err)

    def _board_fingerprint(self) -> tuple[Any, ...]:
        featured = self.featured_game
        return (
            games_fingerprint(self.games),
            self.pinned_game_id,
            (
                featured.away.coach_name if featured and featured.away else "",
                featured.away.coach_years if featured and featured.away else None,
                featured.home.coach_name if featured and featured.home else "",
                featured.home.coach_years if featured and featured.home else None,
            ),
            tuple(
                (row.get("line"), row.get("player"), row.get("value"))
                for row in self.featured_leaders
            ),
            (self.featured_odds or {}).get("line"),
            tuple(
                (row.get("line"), row.get("points"))
                for row in self.fantasy_players
            ),
            self.fantasy_error,
        )

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

    def _poll_due(self) -> bool:
        """Live games refresh on the short tick; idle uses configured interval."""
        now = time.monotonic()
        last = self._last_poll_monotonic
        if last is None:
            return True
        elapsed = now - last
        if self.live:
            return elapsed >= LIVE_REFRESH_SECONDS
        return elapsed >= self.refresh_seconds

    async def _keepalive_task(self) -> None:
        if not self._poll_due():
            return
        # Stamp at start so a slow PNG/enrich cannot stretch the live interval to 2×.
        self._last_poll_monotonic = time.monotonic()
        changed = await self.async_refresh()
        if changed:
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

    async def _write_board_json(self) -> None:
        payload = self.board

        def _write() -> None:
            path = self._json_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        await self.hass.async_add_executor_job(_write)

    async def _write_board_png(self) -> None:
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

        await self.hass.async_add_executor_job(_write)

    async def _write_board_image(self) -> None:
        """Write JSON then PNG (used by Cast / manual refresh paths)."""
        await self._write_board_json()
        await self._write_board_png()

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
