"""ESPN Fantasy Football helpers — your starters in a live NFL game."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

# ESPN fantasy proTeamId → NFL abbreviation used on the public scoreboard.
PRO_TEAM_ABBR = {
    1: "ATL",
    2: "BUF",
    3: "CHI",
    4: "CIN",
    5: "CLE",
    6: "DAL",
    7: "DEN",
    8: "DET",
    9: "GB",
    10: "TEN",
    11: "IND",
    12: "KC",
    13: "LV",
    14: "LAR",
    15: "MIA",
    16: "MIN",
    17: "NE",
    18: "NO",
    19: "NYG",
    20: "NYJ",
    21: "PHI",
    22: "ARI",
    23: "PIT",
    24: "LAC",
    25: "SF",
    26: "SEA",
    27: "TB",
    28: "WSH",
    29: "CAR",
    30: "JAX",
    33: "BAL",
    34: "HOU",
}

POSITION_BY_DEFAULT = {
    1: "QB",
    2: "RB",
    3: "WR",
    4: "TE",
    5: "K",
    16: "D/ST",
}

# Bench / IR / taxi — excluded from the live-game strip.
BENCH_SLOTS = frozenset({20, 21, 22})


@dataclass(frozen=True)
class FantasyPlayer:
    name: str
    position: str
    team: str
    points: float
    starter: bool

    def as_dict(self) -> dict[str, Any]:
        pts = self.points
        points_label = f"{pts:g}" if pts == int(pts) else f"{pts:.1f}"
        return {
            "name": self.name,
            "position": self.position,
            "team": self.team,
            "points": pts,
            "points_label": points_label,
            "line": f"{self.position} {self.name} ({self.team}) {points_label}",
        }


def current_fantasy_season(now: datetime | None = None) -> int:
    """NFL fantasy season year flips in March."""
    stamp = now or datetime.now().astimezone()
    return stamp.year if stamp.month >= 3 else stamp.year - 1


def players_in_game(
    payload: dict[str, Any] | None,
    *,
    team_id: int,
    away_abbr: str,
    home_abbr: str,
) -> list[dict[str, str]]:
    """Starters on your fantasy team whose NFL club is in the featured game."""
    players = parse_team_roster(payload, team_id)
    teams = {away_abbr.upper(), home_abbr.upper()} - {""}
    matched = [
        player
        for player in players
        if player.starter and player.team.upper() in teams
    ]
    matched.sort(key=lambda item: (-item.points, item.name))
    return [player.as_dict() for player in matched]


def parse_team_roster(payload: dict[str, Any] | None, team_id: int) -> list[FantasyPlayer]:
    if not isinstance(payload, dict):
        return []
    teams = payload.get("teams")
    if not isinstance(teams, list):
        return []
    target = None
    for team in teams:
        if isinstance(team, dict) and int(team.get("id") or -1) == int(team_id):
            target = team
            break
    if target is None:
        return []
    roster = target.get("roster") if isinstance(target.get("roster"), dict) else {}
    entries = roster.get("entries")
    if not isinstance(entries, list):
        return []
    players: list[FantasyPlayer] = []
    for entry in entries:
        player = _parse_entry(entry)
        if player is not None:
            players.append(player)
    return players


def _parse_entry(entry: object) -> FantasyPlayer | None:
    if not isinstance(entry, dict):
        return None
    raw_slot = entry.get("lineupSlotId")
    try:
        slot = int(raw_slot) if raw_slot is not None else -1
    except (TypeError, ValueError):
        slot = -1
    pool = entry.get("playerPoolEntry")
    if not isinstance(pool, dict):
        return None
    player = pool.get("player") if isinstance(pool.get("player"), dict) else {}
    name = str(
        player.get("fullName")
        or player.get("lastName")
        or player.get("displayName")
        or ""
    ).strip()
    if not name:
        return None
    pro_id = int(player.get("proTeamId") or 0)
    team = PRO_TEAM_ABBR.get(pro_id, "")
    default_pos = int(player.get("defaultPositionId") or 0)
    position = POSITION_BY_DEFAULT.get(default_pos, "FLEX")
    points = _points(pool, player)
    return FantasyPlayer(
        name=name,
        position=position,
        team=team,
        points=points,
        starter=slot not in BENCH_SLOTS and slot >= 0,
    )


def _points(pool: dict[str, Any], player: dict[str, Any]) -> float:
    raw = pool.get("appliedStatTotal")
    if isinstance(raw, (int, float)):
        return float(raw)
    stats = player.get("stats")
    if isinstance(stats, list):
        for row in stats:
            if not isinstance(row, dict):
                continue
            applied = row.get("appliedTotal")
            if isinstance(applied, (int, float)):
                return float(applied)
    return 0.0
