"""Fetch scoreboards, weather, and optional geocoding."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any
from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import OPEN_METEO_FORECAST, OPEN_METEO_GEOCODE, SCOPE_TODAY
from .distance import has_coords
from .espn import parse_scoreboard, scoreboard_url
from .games import Game, on_todays_board, sort_games
from .weather import parse_open_meteo

_LOGGER = logging.getLogger(__name__)
TIMEOUT = ClientTimeout(total=12)
# ESPN returns 403 for User-Agents that contain "HomeAssistant".
HEADERS = {
    "User-Agent": "SportsWall/1.0 (+https://github.com/gmisner/ha-sportswall)",
    "Accept": "application/json",
}


class SportsClient:
    """Talk to ESPN and Open-Meteo with a shared aiohttp session."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._geo_cache: dict[str, tuple[float, float] | None] = {}
        self._weather_cache: dict[tuple[float, float], tuple[float | None, str, str]] = {}

    async def fetch_games(
        self,
        leagues: list[str],
        now: datetime,
        scope: str = SCOPE_TODAY,
    ) -> list[Game]:
        date_keys = [None]
        if scope == SCOPE_TODAY:
            date_keys = [
                now.strftime("%Y%m%d"),
                (now - timedelta(days=1)).strftime("%Y%m%d"),
            ]
        jobs = [
            self._scoreboard(league, date_key)
            for league in leagues
            for date_key in date_keys
        ]
        results = await asyncio.gather(*jobs, return_exceptions=True)
        games: list[Game] = []
        seen: set[str] = set()
        errors: list[Exception] = []
        for result in results:
            if isinstance(result, Exception):
                errors.append(result)
                _LOGGER.warning("Sports Wall could not load a scoreboard: %s", result)
                continue
            for game in result:
                if game.id in seen:
                    continue
                seen.add(game.id)
                games.append(game)
        if scope == SCOPE_TODAY:
            games = [game for game in games if on_todays_board(game, now)]
        if not games and errors:
            raise errors[0]
        await self._enrich_weather(games)
        return sort_games(games)

    async def _scoreboard(self, league: str, date_key: str | None) -> list[Game]:
        payload = await self._json(scoreboard_url(league, date_key))
        if not isinstance(payload, dict):
            return []
        return parse_scoreboard(payload, league)

    async def _enrich_weather(self, games: list[Game]) -> None:
        pending = [game for game in games if game.weather_temp_f is None or not game.weather_text]
        if not pending:
            return
        await asyncio.gather(*[self._fill_weather(game) for game in pending], return_exceptions=True)

    async def _fill_weather(self, game: Game) -> None:
        coords = await self._coords_for(game)
        if coords is None:
            return
        lat, lon = coords
        cached = self._weather_cache.get((round(lat, 2), round(lon, 2)))
        if cached is None:
            payload = await self._json(
                OPEN_METEO_FORECAST,
                params={
                    "latitude": f"{lat:.4f}",
                    "longitude": f"{lon:.4f}",
                    "current": "temperature_2m,weather_code",
                    "temperature_unit": "fahrenheit",
                },
            )
            if not isinstance(payload, dict):
                return
            cached = parse_open_meteo(payload)
            self._weather_cache[(round(lat, 2), round(lon, 2))] = cached
        temp, text, icon = cached
        if game.weather_temp_f is None:
            game.weather_temp_f = temp
        if not game.weather_text:
            game.weather_text = text
            game.weather_icon = icon

    async def _coords_for(self, game: Game) -> tuple[float, float] | None:
        home = game.home
        venue_city = (game.venue_city or "").strip().lower()
        home_city = (home.city if home else "").strip().lower()
        if venue_city and home_city and venue_city not in home_city and home_city not in venue_city:
            query = ", ".join(part for part in (game.venue_city, game.venue_region) if part)
            geo = await self._geocode(query)
            if geo is not None:
                return geo
        if home and has_coords(home.latitude, home.longitude):
            return home.latitude, home.longitude
        query = ", ".join(part for part in (game.venue_city, game.venue_region) if part)
        return await self._geocode(query) if query else None

    async def _geocode(self, query: str) -> tuple[float, float] | None:
        key = query.strip().lower()
        if key in self._geo_cache:
            return self._geo_cache[key]
        payload = await self._json(
            OPEN_METEO_GEOCODE,
            params={"name": query, "count": "1", "language": "en", "format": "json"},
        )
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list) or not results:
            self._geo_cache[key] = None
            return None
        first = results[0]
        try:
            coords = (float(first["latitude"]), float(first["longitude"]))
        except (KeyError, TypeError, ValueError):
            self._geo_cache[key] = None
            return None
        self._geo_cache[key] = coords
        return coords

    async def _json(self, url: str, params: dict[str, str] | None = None) -> Any:
        try:
            async with self._session.get(
                url, params=params, timeout=TIMEOUT, headers=HEADERS
            ) as response:
                if response.status != 200:
                    raise ClientError(f"HTTP {response.status} for {url}")
                return await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            _LOGGER.debug("Request failed %s: %s", url, err)
            return None
