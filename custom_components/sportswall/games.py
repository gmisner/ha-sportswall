"""Game records shown on the Sports Wall board."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .const import LEAGUE_LABELS, UNIT_IMPERIAL
from .distance import has_coords, haversine_km, haversine_miles
from .teams import TeamHome, team_home


@dataclass
class TeamSide:
    abbreviation: str
    name: str
    nickname: str
    location: str
    city: str
    region: str
    score: int | None
    winner: bool
    logo_url: str
    color: str
    alt_color: str
    home: bool
    latitude: float | None
    longitude: float | None
    record: str = ""

    @property
    def city_label(self) -> str:
        if self.city and self.region:
            return f"{self.city}, {self.region}"
        return self.city or self.location or self.abbreviation

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["city_label"] = self.city_label
        return payload


@dataclass
class Game:
    id: str
    league: str
    name: str
    short_name: str
    start: datetime | None
    status: str
    status_detail: str
    period: str
    clock: str
    venue: str
    venue_city: str
    venue_region: str
    indoor: bool
    broadcasts: list[str] = field(default_factory=list)
    away: TeamSide | None = None
    home: TeamSide | None = None
    weather_text: str | None = None
    weather_temp_f: float | None = None
    weather_icon: str = "unknown"
    travel_miles: float | None = None
    travel_km: float | None = None

    @property
    def league_label(self) -> str:
        return LEAGUE_LABELS.get(self.league, self.league.upper())

    @property
    def network(self) -> str:
        return ", ".join(self.broadcasts) if self.broadcasts else "TBD"

    @property
    def is_live(self) -> bool:
        return self.status == "in"

    @property
    def is_final(self) -> bool:
        return self.status == "post"

    @property
    def venue_label(self) -> str:
        place = ", ".join(part for part in (self.venue_city, self.venue_region) if part)
        if self.venue and place:
            return f"{self.venue} · {place}"
        return self.venue or place or "TBD"

    def apply_homes(self, lookup: dict[tuple[str, str], TeamHome] | None = None) -> None:
        """Fill city/coords from the static table, then compute travel."""
        for side in (self.away, self.home):
            if side is None:
                continue
            home = None
            if lookup is not None:
                home = lookup.get((self.league, side.abbreviation.upper()))
            if home is None:
                home = team_home(self.league, side.abbreviation, side.location)
            if home is None:
                continue
            if home.city:
                side.city = home.city
            if home.region:
                side.region = home.region
            if has_coords(home.latitude, home.longitude):
                side.latitude = home.latitude
                side.longitude = home.longitude
        self.refresh_travel()

    def refresh_travel(self) -> None:
        if (
            self.away is None
            or self.home is None
            or not has_coords(self.away.latitude, self.away.longitude)
            or not has_coords(self.home.latitude, self.home.longitude)
        ):
            self.travel_miles = None
            self.travel_km = None
            return
        assert self.away.latitude is not None and self.away.longitude is not None
        assert self.home.latitude is not None and self.home.longitude is not None
        self.travel_km = haversine_km(
            self.away.latitude,
            self.away.longitude,
            self.home.latitude,
            self.home.longitude,
        )
        self.travel_miles = haversine_miles(
            self.away.latitude,
            self.away.longitude,
            self.home.latitude,
            self.home.longitude,
        )

    def travel_label(self, units: str = UNIT_IMPERIAL) -> str:
        if self.travel_miles is None or self.travel_km is None:
            return ""
        if self.travel_miles < 15:
            return "Local"
        if units == UNIT_IMPERIAL:
            return f"{self.travel_miles:,.0f} mi"
        return f"{self.travel_km:,.0f} km"

    def cities_route(self) -> str:
        if self.away is None or self.home is None:
            return ""
        return f"{self.away.city or self.away.location} → {self.home.city or self.home.location}"

    def as_dict(self, units: str = UNIT_IMPERIAL) -> dict[str, Any]:
        payload = asdict(self)
        payload["start"] = self.start.isoformat() if self.start else None
        payload["league_label"] = self.league_label
        payload["network"] = self.network
        payload["is_live"] = self.is_live
        payload["is_final"] = self.is_final
        payload["venue_label"] = self.venue_label
        payload["travel_label"] = self.travel_label(units)
        payload["cities_route"] = self.cities_route()
        payload["temp_label"] = _temp_label(self.weather_temp_f, units)
        if self.away is not None:
            payload["away"] = self.away.as_dict()
        if self.home is not None:
            payload["home"] = self.home.as_dict()
        return payload


def _temp_label(temp_f: float | None, units: str) -> str:
    if temp_f is None:
        return ""
    if units == UNIT_IMPERIAL:
        return f"{int(round(temp_f))}°F"
    celsius = (temp_f - 32) * 5 / 9
    return f"{int(round(celsius))}°C"


def on_todays_board(game: Game, now: datetime) -> bool:
    """Live games always show; others must start on the local calendar day."""
    if game.is_live:
        return True
    if game.start is None:
        return False
    start = game.start
    if start.tzinfo is not None and now.tzinfo is not None:
        start = start.astimezone(now.tzinfo)
    return start.date() == now.date()


def sort_games(games: list[Game]) -> list[Game]:
    """Live games first, then start time, then finals."""

    def key(game: Game) -> tuple[int, datetime | float, str]:
        if game.is_live:
            bucket = 0
        elif game.is_final:
            bucket = 2
        else:
            bucket = 1
        when = game.start or datetime.max.replace(tzinfo=None)
        if when.tzinfo is not None:
            when = when.replace(tzinfo=None)
        return (bucket, when, game.short_name)

    return sorted(games, key=key)
