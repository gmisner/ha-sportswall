"""Board payload used by the PNG renderer and the tablet HTML page."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .artifacts import ARTIFACTS_TITLE, build_artifacts
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
# {{ b.md_score }}

## {{ b.md_status }}

{% if b.md_cities %}### {{ b.md_cities }}{% endif %}

{% if b.md_artifacts %}**{{ b.artifacts_title }}** · {{ b.md_artifacts }}{% endif %}
{% if b.md_leaders %}

**Leaders** · {{ b.md_leaders }}
{% endif %}
{% if b.md_fantasy %}

**Your players** · {{ b.md_fantasy }}
{% endif %}
{% if b.md_ticker %}

{{ b.md_ticker }}
{% endif %}
{% else %}
# {{ b.clock }}

## NO GAMES TODAY

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


def resolve_featured(
    games: list[Game],
    featured_game_id: str | None = None,
) -> Game | None:
    """Pinned game if still on the board; otherwise the auto-sorted headliner."""
    ordered = sort_games(games)
    if not ordered:
        return None
    if featured_game_id:
        for game in ordered:
            if game.id == featured_game_id:
                return game
    return ordered[0]


def build_board(
    games: list[Game],
    now: datetime,
    *,
    units: str = UNIT_IMPERIAL,
    theme: str = DEFAULT_THEME,
    ui_theme: str | None = None,
    board_view: str = "game",
    time_format: str = TIME_FOLLOW_UNITS,
    show_logos: bool = True,
    leagues: list[str] | None = None,
    next_game: Game | None = None,
    featured_game_id: str | None = None,
    leaders: list[dict[str, str]] | None = None,
    odds: dict[str, str] | None = None,
    fantasy_players: list[dict[str, str]] | None = None,
    fantasy_enabled: bool = False,
    fantasy_error: str | None = None,
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
    featured_game = resolve_featured(ordered, featured_game_id)
    featured = None
    if featured_game is not None:
        featured = next((card for card in cards if card.get("id") == featured_game.id), None)
    if featured is not None:
        featured["leaders"] = list(leaders or [])
        featured["odds"] = odds if isinstance(odds, dict) and odds.get("line") else None
        featured["fantasy_players"] = list(fantasy_players or [])
        featured["pinned"] = bool(
            featured_game_id and featured_game and featured_game.id == featured_game_id
        )
    payload = {
        "title": "Sports Wall",
        "clock": format_clock(now, units, time_format),
        "date": f"{now.strftime('%A, %B')} {now.day}",
        "subtitle": subtitle,
        "theme": theme,
        "ui_theme": ui_theme or theme,
        "board_view": board_view,
        "data_source": "live",
        "units": units,
        "show_logos": show_logos,
        "live_count": live,
        "final_count": finals,
        "game_count": len(ordered),
        "leagues": league_names,
        "featured": featured,
        "featured_game_id": featured_game.id if featured_game else None,
        "games": cards,
        "next_game": _card(upcoming, now, units, time_format, show_logos) if upcoming and not ordered else None,
        "empty": not ordered,
        "has_games": bool(cards),
        "fantasy_enabled": bool(fantasy_enabled),
        "fantasy_error": fantasy_error or "",
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
    situation = (
        game.situation_text or game.status_detail or status_meta or ""
    ).strip()
    possession = game.possession if game.is_live and game.possession in {"away", "home"} else ""
    payload.update(
        {
            "status_label": status,
            "status_kind": status_kind,
            "status_meta": status_meta,
            "situation": situation,
            "possession": possession,
            "show_logos": show_logos,
            "weather_line": _weather_line(payload),
            "away_score": _score_text(game.away.score if game.away else None, game.status),
            "home_score": _score_text(game.home.score if game.home else None, game.status),
            "away_record": (game.away.record if game.away else "") or "",
            "home_record": (game.home.record if game.home else "") or "",
        }
    )
    payload["artifacts"] = build_artifacts(payload, units)
    payload["artifacts_title"] = ARTIFACTS_TITLE
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
            "md_artifacts": "",
            "artifacts_title": ARTIFACTS_TITLE,
            "md_leaders": "",
            "md_fantasy": "",
            "md_ticker": "",
            "away_logo": "",
            "home_logo": "",
        }
    away = featured.get("away") or {}
    home = featured.get("home") or {}
    away_ab = str(away.get("abbreviation") or "?")
    home_ab = str(home.get("abbreviation") or "?")
    vs = "@" if featured.get("status_kind") == "pre" else "-"
    cities = featured.get("cities_route") or ""
    artifacts = list(featured.get("artifacts") or [])
    rest = [card for card in cards if card.get("id") != featured.get("id")]
    status = str(featured.get("status_label") or "")
    detail = str(featured.get("status_meta") or "")
    league = str(featured.get("league_label") or "")
    network = str(featured.get("network") or "")
    status_bits = [status]
    if detail and detail not in {status, "TBD"}:
        status_bits.append(detail)
    if league:
        status_bits.append(league)
    if network and network != "TBD":
        status_bits.append(network)
    artifacts_body = " · ".join(
        f"{item.get('label')}: {item.get('value')}"
        for item in artifacts
        if item.get("value")
    )
    return {
        "md_status": " · ".join(status_bits),
        "md_league": " · ".join(bit for bit in (league, network) if bit),
        "md_score": (
            f"{away_ab}  {featured.get('away_score')}  {vs}  "
            f"{featured.get('home_score')}  {home_ab}"
        ),
        "md_cities": cities,
        "md_detail": detail or status,
        "md_facts": artifacts_body,
        "md_artifacts": artifacts_body,
        "artifacts_title": featured.get("artifacts_title") or ARTIFACTS_TITLE,
        "md_leaders": "  ·  ".join(
            str(row.get("line") or "")
            for row in (featured.get("leaders") or [])
            if row.get("line")
        ),
        "md_fantasy": "  ·  ".join(
            str(row.get("line") or "")
            for row in (featured.get("fantasy_players") or [])
            if row.get("line")
        ),
        "md_ticker": "  ·  ".join(_ticker_line(card) for card in rest[:8]),
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
    return " · ".join(bit for bit in bits if bit).strip()


def _score_text(score: int | None, status: str) -> str:
    if status == "pre" or score is None:
        return "—"
    return str(score)


def local_now(timezone: str | None) -> datetime:
    try:
        return datetime.now(ZoneInfo(timezone or "UTC"))
    except (KeyError, ValueError):
        return datetime.now().astimezone()
