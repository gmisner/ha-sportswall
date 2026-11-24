"""Parse ESPN game-summary leaders into a short board strip."""

from __future__ import annotations

from typing import Any

from .const import LEAGUE_MLB, LEAGUE_NBA, LEAGUE_NCAAB, LEAGUE_NCAAF, LEAGUE_NFL, LEAGUE_NHL

PREFERRED = {
    LEAGUE_NFL: ("Passing Yards", "Rushing Yards", "Receiving Yards"),
    LEAGUE_NCAAF: ("Passing Yards", "Rushing Yards", "Receiving Yards"),
    LEAGUE_NBA: ("Points", "Rebounds", "Assists"),
    LEAGUE_NCAAB: ("Points", "Rebounds", "Assists"),
    LEAGUE_MLB: ("Hits", "Home Runs", "Strikeouts"),
    LEAGUE_NHL: ("Goals", "Assists", "Saves"),
}

MAX_LEADERS = 6


def parse_leaders(payload: dict[str, Any] | None, league: str) -> list[dict[str, str]]:
    """Flatten ESPN summary leaders into compact board rows."""
    if not isinstance(payload, dict):
        return []
    rows = _flatten(payload.get("leaders"))
    if not rows:
        return []
    preferred = PREFERRED.get(league, ())
    picked: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(row: dict[str, str]) -> None:
        key = (row["category"], row["player"])
        if key in seen or len(picked) >= MAX_LEADERS:
            return
        seen.add(key)
        picked.append(row)

    for category in preferred:
        for row in rows:
            if row["category"] == category:
                add(row)
    for row in rows:
        add(row)
    return picked


def _flatten(leaders: object) -> list[dict[str, str]]:
    if not isinstance(leaders, list):
        return []
    rows: list[dict[str, str]] = []
    for team_block in leaders:
        if not isinstance(team_block, dict):
            continue
        team = _clean((team_block.get("team") or {}).get("abbreviation"))
        categories = team_block.get("leaders")
        if not isinstance(categories, list):
            continue
        for category in categories:
            if not isinstance(category, dict):
                continue
            label = _clean(category.get("displayName") or category.get("name"))
            entries = category.get("leaders")
            if not label or not isinstance(entries, list) or not entries:
                continue
            top = entries[0]
            if not isinstance(top, dict):
                continue
            athlete = top.get("athlete") if isinstance(top.get("athlete"), dict) else {}
            player = _clean(
                athlete.get("shortName")
                or athlete.get("displayName")
                or athlete.get("fullName")
            )
            value = _clean(top.get("displayValue"))
            if not player or not value:
                continue
            rows.append(
                {
                    "team": team,
                    "category": label,
                    "player": player,
                    "value": value,
                    "line": f"{team + ' ' if team else ''}{player} · {label} · {value}".strip(),
                }
            )
    return rows


def _clean(value: object) -> str:
    return str(value or "").strip()
