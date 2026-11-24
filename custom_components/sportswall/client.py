"""Fetch scoreboards, weather, fantasy, and optional geocoding."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any
from aiohttp import ClientError, ClientSession, ClientTimeout

from .coaches import parse_head_coach, tenure_years_from_person
from .const import (
    ESPN_FANTASY_LEAGUE,
    OPEN_METEO_ELEVATION,
    OPEN_METEO_FORECAST,
    OPEN_METEO_GEOCODE,
    SCOPE_TODAY,
)
from .distance import has_coords
from .espn import (
    athlete_statisticslog_url,
    coach_person_url,
    depthchart_url,
    parse_scoreboard,
    roster_url,
    scoreboard_url,
    summary_url,
    venue_url,
)
from .fantasy_espn import current_fantasy_season, players_in_game
from .games import Game, TeamSide, on_todays_board, sort_games
from .leaders import parse_leaders
from .odds import parse_odds
from .roster_facts import (
    average_oline_weight_lb,
    oline_depth_ids,
    parse_roster_athletes,
    starter_qb,
    tenure_years_from_statisticslog,
)
from .weather import parse_open_meteo

_LOGGER = logging.getLogger(__name__)
TIMEOUT = ClientTimeout(total=12)
# ESPN returns 403 for User-Agents that contain "HomeAssistant".
HEADERS = {
    "User-Agent": "SportsWall/1.0 (+https://github.com/gmisner/ha-sportswall)",
    "Accept": "application/json",
}
_COACH_LEAGUES = frozenset({"nfl", "nba", "mlb", "nhl", "ncaaf", "ncaab"})
_FOOTBALL_LEAGUES = frozenset({"nfl", "ncaaf"})


class SportsClient:
    """Talk to ESPN and Open-Meteo with a shared aiohttp session."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._geo_cache: dict[str, tuple[float, float] | None] = {}
        self._weather_cache: dict[
            tuple[float, float], tuple[float | None, str, str, float | None]
        ] = {}
        self._elevation_cache: dict[tuple[float, float], float | None] = {}
        self._leaders_cache: dict[str, list[dict[str, str]]] = {}
        self._odds_cache: dict[str, dict[str, str] | None] = {}
        self._fantasy_cache: dict[str, list[dict[str, str]]] = {}
        self._coach_cache: dict[str, tuple[str, int | None, str]] = {}
        self._roster_cache: dict[str, dict[str, Any] | None] = {}
        self._depth_cache: dict[str, dict[str, Any] | None] = {}
        self._qb_tenure_cache: dict[str, int | None] = {}
        self._surface_cache: dict[str, str] = {}
        self._venue_cache: dict[str, tuple[str, str] | None] = {}
        self.fantasy_error: str | None = None

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
        await self._enrich_travel(games)
        await self._enrich_weather(games)
        await self._enrich_elevation(games)
        return sort_games(games)

    async def _scoreboard(self, league: str, date_key: str | None) -> list[Game]:
        payload = await self._json(scoreboard_url(league, date_key))
        if not isinstance(payload, dict):
            return []
        return parse_scoreboard(payload, league)

    async def fetch_leaders(self, game: Game) -> list[dict[str, str]]:
        """Box-score leaders for the featured game (cached per event id)."""
        leaders, _odds = await self.fetch_summary_extras(game)
        return leaders

    async def fetch_odds(self, game: Game) -> dict[str, str] | None:
        """Vegas / sportsbook line from ESPN pickcenter for the featured game."""
        _leaders, odds = await self.fetch_summary_extras(game)
        return odds

    async def fetch_summary_extras(
        self, game: Game
    ) -> tuple[list[dict[str, str]], dict[str, str] | None]:
        """One ESPN summary call → leaders + odds."""
        cached_leaders = self._leaders_cache.get(game.id)
        cached_odds = self._odds_cache.get(game.id)
        if cached_leaders is not None and cached_odds is not None and not game.is_live:
            return cached_leaders, cached_odds
        if game.league not in {
            "nfl",
            "nba",
            "mlb",
            "nhl",
            "ncaaf",
            "ncaab",
        }:
            return [], None
        payload = await self._json(summary_url(game.league, game.id))
        body = payload if isinstance(payload, dict) else None
        leaders = parse_leaders(body, game.league)
        odds = parse_odds(body)
        self._leaders_cache[game.id] = leaders
        self._odds_cache[game.id] = odds
        return leaders, odds

    async def enrich_coaches(self, game: Game) -> None:
        """Fill head coach + tenure years on both sides (featured only)."""
        await self.enrich_team_facts(game)

    async def enrich_team_facts(self, game: Game) -> None:
        """Coaches, surface, QB, and O-line facts for the featured matchup."""
        await asyncio.gather(
            self._fill_team_facts(game.league, game.away),
            self._fill_team_facts(game.league, game.home),
            self._fill_surface(game),
            return_exceptions=True,
        )

    async def enrich_travel(self, game: Game) -> None:
        """Resolve campus/stadium coords (college lacks TEAM_HOMES) then travel."""
        await self._fill_game_travel(game)

    async def _enrich_travel(self, games: list[Game]) -> None:
        pending = [game for game in games if game.travel_miles is None]
        if not pending:
            return
        await asyncio.gather(
            *[self._fill_game_travel(game) for game in pending],
            return_exceptions=True,
        )

    async def _fill_game_travel(self, game: Game) -> None:
        await asyncio.gather(
            self._fill_side_coords(game, game.away),
            self._fill_side_coords(game, game.home),
            return_exceptions=True,
        )
        # Game venue is a solid fallback for the home side.
        if game.home is not None and not has_coords(game.home.latitude, game.home.longitude):
            await self._apply_geocode(
                game.home,
                ", ".join(part for part in (game.venue_city, game.venue_region) if part),
            )
        game.refresh_travel()

    async def _fill_side_coords(self, game: Game, side: TeamSide | None) -> None:
        if side is None or has_coords(side.latitude, side.longitude):
            return
        venue_id = str(side.home_venue_id or "").strip()
        if venue_id:
            address = await self._venue_address(game.league, venue_id)
            if address is not None:
                city, region = address
                if city:
                    side.city = city
                if region:
                    side.region = region
                query = ", ".join(part for part in (city, region) if part)
                if await self._apply_geocode(side, query):
                    return
        # Avoid bare school nicknames ("Oregon", "Ohio State") — they geocode poorly.
        if side.city and side.region:
            await self._apply_geocode(side, f"{side.city}, {side.region}")

    async def _apply_geocode(self, side: TeamSide, query: str) -> bool:
        clean = query.strip()
        if not clean:
            return False
        coords = await self._geocode(clean)
        if coords is None:
            return False
        side.latitude, side.longitude = coords
        return True

    async def _venue_address(self, league: str, venue_id: str) -> tuple[str, str] | None:
        cache_key = f"{league}:{venue_id}"
        if cache_key in self._venue_cache:
            return self._venue_cache[cache_key]
        payload = await self._json(venue_url(league, venue_id))
        address = payload.get("address") if isinstance(payload, dict) else None
        if not isinstance(address, dict):
            self._venue_cache[cache_key] = None
            return None
        city = str(address.get("city") or "").strip()
        region = str(address.get("state") or address.get("region") or "").strip()
        if not city:
            self._venue_cache[cache_key] = None
            return None
        resolved = (city, region)
        self._venue_cache[cache_key] = resolved
        return resolved

    async def _fill_team_facts(self, league: str, side: TeamSide | None) -> None:
        if side is None:
            return
        team_id = str(side.espn_id or "").strip()
        if not team_id:
            return
        need_coach = league in _COACH_LEAGUES and not (
            side.coach_name and side.coach_years is not None
        )
        need_football = league in _FOOTBALL_LEAGUES and (
            not side.qb_name or side.oline_avg_lb is None
        )
        if not need_coach and not need_football:
            return
        roster = await self._roster_payload(league, team_id)
        if need_coach:
            await self._apply_coach(league, side, team_id, roster)
        if need_football:
            await self._apply_football_facts(league, side, team_id, roster)

    async def _apply_coach(
        self,
        league: str,
        side: TeamSide,
        team_id: str,
        roster: dict[str, Any] | None,
    ) -> None:
        cache_key = f"{league}:{team_id}"
        cached = self._coach_cache.get(cache_key)
        if cached is None:
            cached = parse_head_coach(roster)
            self._coach_cache[cache_key] = cached
        name, years, coach_id = cached
        if name and years is None and coach_id:
            years = await self._coach_tenure_years(league, coach_id)
            self._coach_cache[cache_key] = (name, years, coach_id)
        if name:
            side.coach_name = name
            side.coach_years = years

    async def _apply_football_facts(
        self,
        league: str,
        side: TeamSide,
        team_id: str,
        roster: dict[str, Any] | None,
    ) -> None:
        athletes = parse_roster_athletes(roster)
        depth = await self._depth_payload(league, team_id)
        starter_ids = oline_depth_ids(depth) or None
        if side.oline_avg_lb is None:
            avg = average_oline_weight_lb(athletes, starter_ids)
            if avg is None and starter_ids is not None:
                avg = average_oline_weight_lb(athletes, None)
            side.oline_avg_lb = avg
        if side.qb_name:
            return
        qb_id, qb_name, experience = starter_qb(athletes, depth)
        if not qb_name:
            return
        years = experience
        if qb_id and league == "nfl":
            tenure = await self._qb_team_tenure(league, qb_id, team_id)
            if tenure is not None:
                years = tenure
        side.qb_name = qb_name
        side.qb_years = years


    async def _fill_surface(self, game: Game) -> None:
        if game.surface:
            return
        venue_id = str(game.venue_id or "").strip()
        if not venue_id:
            return
        cache_key = f"{game.league}:{venue_id}"
        if cache_key in self._surface_cache:
            game.surface = self._surface_cache[cache_key]
            return
        payload = await self._json(venue_url(game.league, venue_id))
        surface = ""
        if isinstance(payload, dict) and "grass" in payload:
            surface = "Grass" if bool(payload.get("grass")) else "Turf"
        self._surface_cache[cache_key] = surface
        game.surface = surface

    async def _roster_payload(self, league: str, team_id: str) -> dict[str, Any] | None:
        cache_key = f"{league}:{team_id}"
        if cache_key in self._roster_cache:
            return self._roster_cache[cache_key]
        payload = await self._json(roster_url(league, team_id))
        body = payload if isinstance(payload, dict) else None
        self._roster_cache[cache_key] = body
        return body

    async def _depth_payload(self, league: str, team_id: str) -> dict[str, Any] | None:
        cache_key = f"{league}:{team_id}"
        if cache_key in self._depth_cache:
            return self._depth_cache[cache_key]
        payload = await self._json(depthchart_url(league, team_id))
        body = payload if isinstance(payload, dict) else None
        self._depth_cache[cache_key] = body
        return body

    async def _qb_team_tenure(
        self, league: str, athlete_id: str, team_id: str
    ) -> int | None:
        cache_key = f"{league}:{athlete_id}:{team_id}"
        if cache_key in self._qb_tenure_cache:
            return self._qb_tenure_cache[cache_key]
        payload = await self._json(athlete_statisticslog_url(league, athlete_id))
        years = tenure_years_from_statisticslog(
            payload if isinstance(payload, dict) else None,
            team_id,
        )
        self._qb_tenure_cache[cache_key] = years
        return years

    async def _coach_tenure_years(self, league: str, coach_id: str) -> int | None:
        payload = await self._json(coach_person_url(league, coach_id))
        return tenure_years_from_person(payload if isinstance(payload, dict) else None)

    async def fetch_fantasy_players(
        self,
        game: Game,
        *,
        league_id: str,
        team_id: str,
        espn_s2: str,
        swid: str,
        season: int | None = None,
    ) -> list[dict[str, str]]:
        """Your ESPN Fantasy starters who play in this live NFL game."""
        self.fantasy_error = None
        if not game.is_live or game.league != "nfl":
            return []
        away = (game.away.abbreviation if game.away else "").upper()
        home = (game.home.abbreviation if game.home else "").upper()
        year = season or current_fantasy_season()
        url = ESPN_FANTASY_LEAGUE.format(season=year, league_id=league_id)
        payload = await self._json(
            url,
            params={
                "view": ["mRoster", "mTeam", "mLiveScoring"],
            },
            cookies={"espn_s2": espn_s2, "SWID": swid},
        )
        if not isinstance(payload, dict):
            self.fantasy_error = "Fantasy league request failed"
            return []
        try:
            team_num = int(str(team_id).strip())
        except ValueError:
            self.fantasy_error = "Fantasy team id must be a number"
            return []
        players = players_in_game(
            payload,
            team_id=team_num,
            away_abbr=away,
            home_abbr=home,
        )
        cache_key = f"{league_id}:{team_id}:{game.id}:{away}:{home}"
        self._fantasy_cache[cache_key] = players
        return players

    async def _enrich_weather(self, games: list[Game]) -> None:
        pending = [game for game in games if game.weather_temp_f is None or not game.weather_text]
        if not pending:
            return
        await asyncio.gather(*[self._fill_weather(game) for game in pending], return_exceptions=True)

    async def _enrich_elevation(self, games: list[Game]) -> None:
        pending = [game for game in games if game.elevation_m is None]
        if not pending:
            return
        await asyncio.gather(*[self._fill_elevation(game) for game in pending], return_exceptions=True)

    async def _fill_weather(self, game: Game) -> None:
        coords = await self._coords_for(game)
        if coords is None:
            return
        lat, lon = coords
        key = (round(lat, 2), round(lon, 2))
        cached = self._weather_cache.get(key)
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
            self._weather_cache[key] = cached
            if cached[3] is not None:
                self._elevation_cache[key] = cached[3]
        temp, text, icon, elevation_m = cached
        if game.weather_temp_f is None:
            game.weather_temp_f = temp
        if not game.weather_text:
            game.weather_text = text
            game.weather_icon = icon
        if game.elevation_m is None and elevation_m is not None:
            game.elevation_m = elevation_m

    async def _fill_elevation(self, game: Game) -> None:
        if game.elevation_m is not None:
            return
        coords = await self._coords_for(game)
        if coords is None:
            return
        lat, lon = coords
        key = (round(lat, 2), round(lon, 2))
        if key in self._elevation_cache:
            game.elevation_m = self._elevation_cache[key]
            return
        weather = self._weather_cache.get(key)
        if weather and weather[3] is not None:
            self._elevation_cache[key] = weather[3]
            game.elevation_m = weather[3]
            return
        payload = await self._json(
            OPEN_METEO_ELEVATION,
            params={"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}"},
        )
        elevation_m = None
        if isinstance(payload, dict):
            values = payload.get("elevation")
            if isinstance(values, list) and values:
                try:
                    elevation_m = float(values[0])
                except (TypeError, ValueError):
                    elevation_m = None
        self._elevation_cache[key] = elevation_m
        game.elevation_m = elevation_m

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

    async def _json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> Any:
        try:
            async with self._session.get(
                url,
                params=params,
                timeout=TIMEOUT,
                headers=HEADERS,
                cookies=cookies,
            ) as response:
                if response.status != 200:
                    raise ClientError(f"HTTP {response.status} for {url}")
                return await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            _LOGGER.debug("Request failed %s: %s", url, err)
            return None
