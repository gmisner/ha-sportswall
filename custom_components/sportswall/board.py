"""Board payload used by the PNG renderer and the tablet HTML page."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .const import (
    DEFAULT_THEME,
    LEAGUE_LABELS,
    TIME_12H,
    TIME_24H,
    TIME_FOLLOW_UNITS,
    UNIT_IMPERIAL,
)
from .games import Game, sort_games

DASHBOARD_MARKDOWN = """{% set b = state_attr('__GAMES_ENTITY__','board') or {} %}
{% if b.has_games %}
{% if b.away_logo %}![]({{ b.away_logo }}){% endif %}{% if b.home_logo %} ![]({{ b.home_logo }}){% endif %}

## {{ b.md_status }}{% if b.md_league %} · {{ b.md_league }}{% endif %}

# {{ b.md_score }}

### {{ b.md_cities }}

{{ b.md_detail }}

{{ b.md_facts }}
{% if b.md_ticker %}

---

{{ b.md_ticker }}
{% endif %}
{% else %}
# {{ b.clock }}

### NO GAMES TODAY

{{ b.subtitle }}
{% endif %}
"""


def use_12h(units: str, time_format: str) -> bool:
    if time_format == TIME_12H:
        return True
    if time_format == TIME_24H:
        return False
    return units == UNIT_IMPERIAL or time_format == TIME_FOLLOW_UNITS


def format_clock(now: datetime, units: str, time_format: str) -> str:
    if use_12h(units, time_format):
        return now.strftime("%I:%M %p").lstrip("0").replace("  ", " ")
    return now.strftime("%H:%M")


def format_kickoff(start: datetime | None, now: datetime, units: str, time_format: str) -> str:
    if start is None:
        return "TBD"
    local = start.astimezone(now.tzinfo) if start.tzinfo else start
    clock = format_clock(local, units, time_format)
    if local.date() == now.date():
        return clock
    return f"{local.strftime('%a')} {clock}"


def build_board(
    games: list[Game],
    now: datetime,
    *,
    units: str = UNIT_IMPERIAL,
    theme: str = DEFAULT_THEME,
    time_format: str = TIME_FOLLOW_UNITS,
    show_logos: bool = True,
    leagues: list[str] | None = None,
    next_game: Game | None = None,
) -> dict[str, Any]:
    ordered = sort_games(games)
    live = sum(1 for game in ordered if game.is_live)
    finals = sum(1 for game in ordered if game.is_final)
    league_names = [
        LEAGUE_LABELS.get(item, item.upper())
        for item in (leagues or sorted({game.league for game in ordered}))
    ]
    subtitle = _subtitle(len(ordered), live, league_names)
    cards = [_card(game, now, units, time_format, show_logos) for game in ordered]
    upcoming = next_game
    if upcoming is None:
        upcoming = next((game for game in ordered if game.status == "pre"), None)
    featured = cards[0] if cards else None
    payload = {
        "title": "Sports Wall",
        "clock": format_clock(now, units, time_format),
        "date": f"{now.strftime('%A, %B')} {now.day}",
        "subtitle": subtitle,
        "theme": theme,
        "units": units,
        "show_logos": show_logos,
        "live_count": live,
        "final_count": finals,
        "game_count": len(ordered),
        "leagues": league_names,
        "featured": featured,
        "games": cards,
        "next_game": _card(upcoming, now, units, time_format, show_logos) if upcoming and not ordered else None,
        "empty": not ordered,
        "has_games": bool(cards),
    }
    payload.update(_markdown_copy(cards, featured, show_logos))
    return payload


def _subtitle(count: int, live: int, leagues: list[str]) -> str:
    league_bit = " · ".join(leagues) if leagues else "All leagues"
    if count == 0:
        return f"No games today · {league_bit}"
    games = "1 game" if count == 1 else f"{count} games"
    if live:
        live_bit = "1 live" if live == 1 else f"{live} live"
        return f"{games} today · {live_bit} · {league_bit}"
    return f"{games} today · {league_bit}"


def _card(
    game: Game,
    now: datetime,
    units: str,
    time_format: str,
    show_logos: bool,
) -> dict[str, Any]:
    payload = game.as_dict(units)
    if game.is_live:
        status = "LIVE"
        status_kind = "live"
        if game.period and game.clock:
            status_meta = f"{game.period} {game.clock}"
        else:
            status_meta = game.period or game.status_detail or "In progress"
    elif game.is_final:
        status = "FINAL"
        status_kind = "final"
        status_meta = game.status_detail or "Final"
    else:
        status = format_kickoff(game.start, now, units, time_format)
        status_kind = "pre"
        status_meta = game.status_detail or status
    payload.update(
        {
            "status_label": status,
            "status_kind": status_kind,
            "status_meta": status_meta,
            "show_logos": show_logos,
            "weather_line": _weather_line(payload),
            "away_score": _score_text(game.away.score if game.away else None, game.status),
            "home_score": _score_text(game.home.score if game.home else None, game.status),
        }
    )
    return payload


def _markdown_copy(
    cards: list[dict[str, Any]],
    featured: dict[str, Any] | None,
    show_logos: bool,
) -> dict[str, Any]:
    """Flattened strings for the Cast-safe Lovelace markdown card."""
    if not featured:
        return {
            "md_status": "",
            "md_league": "",
            "md_score": "",
            "md_cities": "",
            "md_detail": "",
            "md_facts": "",
            "md_ticker": "",
            "away_logo": "",
            "home_logo": "",
        }
    away = featured.get("away") or {}
    home = featured.get("home") or {}
    away_ab = str(away.get("abbreviation") or "?")
    home_ab = str(home.get("abbreviation") or "?")
    vs = "@" if featured.get("status_kind") == "pre" else "-"
    travel = featured.get("travel_label") or ""
    cities = featured.get("cities_route") or ""
    travel_line = " · ".join(bit for bit in (travel, cities) if bit) or "TBD"
    weather = featured.get("weather_line") or ("Indoor" if featured.get("indoor") else "TBD")
    rest = [card for card in cards if card.get("id") != featured.get("id")]
    return {
        "md_status": str(featured.get("status_label") or ""),
        "md_league": " · ".join(
            bit
            for bit in (featured.get("league_label"), featured.get("network"))
            if bit
        ),
        "md_score": (
            f"{away_ab}  {featured.get('away_score')}  {vs}  "
            f"{featured.get('home_score')}  {home_ab}"
        ),
        "md_cities": cities,
        "md_detail": str(featured.get("status_meta") or featured.get("status_label") or ""),
        "md_facts": "\n\n".join(
            [
                f"TV {featured.get('network') or 'TBD'}",
                f"WX {weather}",
                f"VENUE {featured.get('venue') or featured.get('venue_label') or 'TBD'}",
                f"TRAVEL {travel_line}",
            ]
        ),
        "md_ticker": "\n\n".join(_ticker_line(card) for card in rest),
        "away_logo": str(away.get("logo_url") or "") if show_logos else "",
        "home_logo": str(home.get("logo_url") or "") if show_logos else "",
    }


def _ticker_line(card: dict[str, Any]) -> str:
    away = card.get("away") or {}
    home = card.get("home") or {}
    away_ab = away.get("abbreviation") or "?"
    home_ab = home.get("abbreviation") or "?"
    if card.get("status_kind") == "pre":
        match = f"{away_ab} @ {home_ab}"
    else:
        match = (
            f"{away_ab} {card.get('away_score')} - {card.get('home_score')} {home_ab}"
        )
    bits = [match, card.get("status_label"), card.get("network")]
    return " · ".join(str(bit) for bit in bits if bit)


def _weather_line(payload: dict[str, Any]) -> str:
    bits = [payload.get("temp_label") or "", payload.get("weather_text") or ""]
    return " ".join(bit for bit in bits if bit).strip()


def _score_text(score: int | None, status: str) -> str:
    if status == "pre" or score is None:
        return "—"
    return str(score)


def local_now(timezone: str | None) -> datetime:
    try:
        return datetime.now(ZoneInfo(timezone or "UTC"))
    except (KeyError, ValueError):
        return datetime.now().astimezone()
