"""Parse ESPN public scoreboard payloads. No network I/O here."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .const import (
    ESPN_SCOREBOARD,
    LEAGUE_MLB,
    LEAGUE_NBA,
    LEAGUE_NCAAB,
    LEAGUE_NCAAF,
    LEAGUE_NFL,
    LEAGUE_NHL,
)
from .games import Game, TeamSide
from .weather import icon_from_text

LEAGUE_PATHS: dict[str, tuple[str, str]] = {
    LEAGUE_NFL: ("football", "nfl"),
    LEAGUE_NBA: ("basketball", "nba"),
    LEAGUE_MLB: ("baseball", "mlb"),
    LEAGUE_NHL: ("hockey", "nhl"),
    LEAGUE_NCAAF: ("football", "college-football"),
    LEAGUE_NCAAB: ("basketball", "mens-college-basketball"),
}


def scoreboard_url(league: str, date_yyyymmdd: str | None = None) -> str:
    sport, slug = LEAGUE_PATHS[league]
    url = ESPN_SCOREBOARD.format(sport=sport, league=slug)
    if date_yyyymmdd:
        return f"{url}?dates={date_yyyymmdd}"
    return url


def parse_scoreboard(payload: dict[str, Any], league: str) -> list[Game]:
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        return []
    games: list[Game] = []
    for event in events:
        game = _parse_event(event, league)
        if game is not None:
            games.append(game)
    return games


def _parse_event(event: dict[str, Any], league: str) -> Game | None:
    if not isinstance(event, dict):
        return None
    competitions = event.get("competitions")
    if not isinstance(competitions, list) or not competitions:
        return None
    competition = competitions[0]
    if not isinstance(competition, dict):
        return None
    competitors = competition.get("competitors")
    if not isinstance(competitors, list):
        return None
    away = home = None
    for item in competitors:
        side = _parse_side(item)
        if side is None:
            continue
        if side.home:
            home = side
        else:
            away = side
    if away is None or home is None:
        return None
    venue = competition.get("venue") if isinstance(competition.get("venue"), dict) else {}
    address = venue.get("address") if isinstance(venue.get("address"), dict) else {}
    status = event.get("status") if isinstance(event.get("status"), dict) else {}
    if not status:
        status = competition.get("status") if isinstance(competition.get("status"), dict) else {}
    status_type = status.get("type") if isinstance(status.get("type"), dict) else {}
    weather = event.get("weather") if isinstance(event.get("weather"), dict) else {}
    if not weather:
        weather = competition.get("weather") if isinstance(competition.get("weather"), dict) else {}
    situation = competition.get("situation") if isinstance(competition.get("situation"), dict) else {}
    broadcasts = _broadcasts(competition)
    start = _parse_when(event.get("date") or competition.get("date") or competition.get("startDate"))
    weather_text = _clean(weather.get("displayValue"))
    if weather_text and weather_text.isdigit():
        weather_text = _clean(weather.get("conditionId")) if not str(weather.get("conditionId", "")).isdigit() else ""
    temp = _number(weather.get("temperature"))
    period = _period_label(league, status, situation)
    clock = _clean(status.get("displayClock"))
    if clock in {"0:00", "0.0"}:
        clock = ""
    game = Game(
        id=str(event.get("id") or competition.get("id") or f"{away.abbreviation}-{home.abbreviation}"),
        league=league,
        name=_clean(event.get("name")) or f"{away.name} at {home.name}",
        short_name=_clean(event.get("shortName")) or f"{away.abbreviation} @ {home.abbreviation}",
        start=start,
        status=_clean(status_type.get("state")) or "pre",
        status_detail=_clean(status_type.get("shortDetail") or status_type.get("detail") or status_type.get("description")),
        period=period,
        clock=clock,
        venue=_clean(venue.get("fullName")),
        venue_city=_clean(address.get("city")),
        venue_region=_clean(address.get("state")),
        indoor=bool(venue.get("indoor")),
        broadcasts=broadcasts,
        away=away,
        home=home,
        weather_text=weather_text or None,
        weather_temp_f=temp,
        weather_icon=icon_from_text(weather_text),
    )
    game.apply_homes()
    return game


def _parse_side(item: Any) -> TeamSide | None:
    if not isinstance(item, dict):
        return None
    team = item.get("team") if isinstance(item.get("team"), dict) else {}
    abbreviation = _clean(team.get("abbreviation")).upper()
    if not abbreviation:
        return None
    home = str(item.get("homeAway") or "").lower() == "home"
    record = ""
    records = item.get("records")
    if isinstance(records, list):
        for row in records:
            if isinstance(row, dict) and str(row.get("type") or "") in {"total", ""}:
                record = _clean(row.get("summary"))
                if record:
                    break
        if not record and records and isinstance(records[0], dict):
            record = _clean(records[0].get("summary"))
    score = _int_or_none(item.get("score"))
    return TeamSide(
        abbreviation=abbreviation,
        name=_clean(team.get("displayName") or team.get("name")) or abbreviation,
        nickname=_clean(team.get("shortDisplayName") or team.get("name") or team.get("nickname"))
        or abbreviation,
        location=_clean(team.get("location")),
        city=_clean(team.get("location")),
        region="",
        score=score,
        winner=bool(item.get("winner")),
        logo_url=_clean(team.get("logo")),
        color=_clean(team.get("color")) or "1a1a1a",
        alt_color=_clean(team.get("alternateColor")) or "ffffff",
        home=home,
        latitude=None,
        longitude=None,
        record=record,
    )


def _broadcasts(competition: dict[str, Any]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        label = _clean(value)
        key = label.lower()
        if not label or key in seen:
            return
        seen.add(key)
        names.append(label)

    broadcasts = competition.get("broadcasts")
    if isinstance(broadcasts, list):
        for item in broadcasts:
            if not isinstance(item, dict):
                continue
            market = str(item.get("market") or "").lower()
            if market in {"away", "home"} and names:
                continue
            for name in item.get("names") or []:
                add(str(name))
    if not names:
        add(str(competition.get("broadcast") or ""))
    geo = competition.get("geoBroadcasts")
    if isinstance(geo, list) and not names:
        for item in geo:
            if not isinstance(item, dict):
                continue
            media = item.get("media") if isinstance(item.get("media"), dict) else {}
            add(str(media.get("shortName") or ""))
    return names


def _period_label(league: str, status: dict[str, Any], situation: dict[str, Any]) -> str:
    detail = _clean((status.get("type") or {}).get("shortDetail")) if isinstance(status.get("type"), dict) else ""
    if league == LEAGUE_MLB:
        inning = _clean(situation.get("inning")) or _clean(status.get("period"))
        half = _clean(situation.get("reason") or situation.get("lastPlay"))
        if "Top" in detail or "Bot" in detail or "End" in detail or "Mid" in detail:
            return detail
        if inning:
            return f"Inn {inning}"
        return detail
    period = status.get("period")
    try:
        number = int(period)
    except (TypeError, ValueError):
        return detail
    if number <= 0:
        return ""
    if league in {LEAGUE_NFL, LEAGUE_NCAAF}:
        if number > 4:
            return "OT"
        return f"Q{number}"
    if league in {LEAGUE_NBA, LEAGUE_NCAAB}:
        if number > 4:
            return f"OT{number - 4}" if number > 5 else "OT"
        return f"Q{number}"
    if league == LEAGUE_NHL:
        if number > 3:
            return "OT"
        return f"P{number}"
    return f"P{number}"


def _parse_when(value: Any) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None
