"""Parse ESPN roster / depth-chart facts for Art'ifacts (QB, O-line)."""

from __future__ import annotations

import re
from typing import Any

from .const import UNIT_IMPERIAL

_TEAM_ID = re.compile(r"/teams/(\d+)")

# Roster position abbreviations that count toward O-line average weight.
_OL_POSITIONS = frozenset({"OT", "G", "C", "OG", "OC", "OL", "T"})
# Depth-chart slots for the starting five.
_OL_DEPTH_SLOTS = ("lt", "lg", "c", "rg", "rt")


def parse_roster_athletes(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Flatten roster groups into athlete dicts (active + IR, skip practice squad)."""
    if not isinstance(payload, dict):
        return []
    groups = payload.get("athletes")
    if not isinstance(groups, list):
        return []
    out: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_name = str(group.get("position") or "").strip().lower()
        if group_name in {"practicesquad", "practice squad", "suspended"}:
            continue
        items = group.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                out.append(item)
    return out


def average_oline_weight_lb(
    athletes: list[dict[str, Any]],
    starter_ids: set[str] | None = None,
) -> float | None:
    """Mean weight (lb) for O-line; prefer depth-chart starters when given."""
    weights: list[float] = []
    for row in athletes:
        athlete_id = _clean(row.get("id"))
        pos = _position_abbr(row)
        if starter_ids is not None:
            if athlete_id not in starter_ids:
                continue
        elif pos not in _OL_POSITIONS:
            continue
        if not _is_usable_player(row):
            continue
        weight = _number(row.get("weight"))
        if weight is not None and weight > 0:
            weights.append(weight)
    if not weights:
        return None
    return sum(weights) / len(weights)


def oline_depth_ids(payload: dict[str, Any] | None) -> set[str]:
    """Starter O-line athlete ids from a depth-chart payload."""
    positions = _offense_positions(payload)
    ids: set[str] = set()
    for slot in _OL_DEPTH_SLOTS:
        row = positions.get(slot)
        if not isinstance(row, dict):
            continue
        athletes = row.get("athletes")
        if not isinstance(athletes, list) or not athletes:
            continue
        first = athletes[0]
        if isinstance(first, dict):
            athlete_id = _clean(first.get("id"))
            if athlete_id:
                ids.add(athlete_id)
    return ids


def starter_qb(
    athletes: list[dict[str, Any]],
    depth_payload: dict[str, Any] | None = None,
) -> tuple[str, str, int | None]:
    """Return (athlete_id, display_name, experience_years) for the current QB."""
    by_id = {_clean(row.get("id")): row for row in athletes if _clean(row.get("id"))}
    depth_id = _depth_qb_id(depth_payload)
    if depth_id and depth_id in by_id:
        row = by_id[depth_id]
        return depth_id, _athlete_name(row), _experience_years(row)
    # No depth chart (common in college): prefer the most experienced active QB.
    qbs: list[tuple[int, str, str, int | None]] = []
    for row in athletes:
        if _position_abbr(row) != "QB":
            continue
        if not _is_usable_player(row):
            continue
        athlete_id = _clean(row.get("id"))
        if not athlete_id:
            continue
        years = _experience_years(row)
        rank = years if years is not None else -1
        qbs.append((rank, athlete_id, _athlete_name(row), years))
    if not qbs:
        return "", "", None
    qbs.sort(key=lambda item: item[0], reverse=True)
    _rank, athlete_id, name, years = qbs[0]
    return athlete_id, name, years


def tenure_years_from_statisticslog(
    payload: dict[str, Any] | None,
    team_id: str,
) -> int | None:
    """Count consecutive seasons (newest first) with the given team."""
    if not isinstance(payload, dict) or not team_id:
        return None
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return None
    want = str(team_id).strip()
    count = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        team_ids = _entry_team_ids(entry)
        if want in team_ids:
            count += 1
        else:
            break
    return count or None


def qb_chip_value(name: str, years: int | None) -> str:
    clean = (name or "").strip()
    if not clean:
        return ""
    if years is None:
        return clean
    unit = "yr" if years == 1 else "yrs"
    return f"{clean} · {years} {unit}"


def oline_chip_value(avg_lb: float | None, units: str = UNIT_IMPERIAL) -> str:
    if avg_lb is None:
        return ""
    if units == UNIT_IMPERIAL:
        return f"{avg_lb:,.0f} lb avg"
    kg = avg_lb * 0.45359237
    return f"{kg:,.0f} kg avg"


def _offense_positions(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    charts = payload.get("depthchart")
    if not isinstance(charts, list):
        return {}
    for chart in charts:
        if not isinstance(chart, dict):
            continue
        positions = chart.get("positions")
        if isinstance(positions, dict) and "qb" in positions:
            return positions
    return {}


def _depth_qb_id(payload: dict[str, Any] | None) -> str:
    positions = _offense_positions(payload)
    row = positions.get("qb")
    if not isinstance(row, dict):
        return ""
    athletes = row.get("athletes")
    if not isinstance(athletes, list) or not athletes:
        return ""
    first = athletes[0]
    if not isinstance(first, dict):
        return ""
    return _clean(first.get("id"))


def _entry_team_ids(entry: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    rows = entry.get("statistics")
    if not isinstance(rows, list):
        return ids
    for row in rows:
        if not isinstance(row, dict) or row.get("type") != "team":
            continue
        team = row.get("team") if isinstance(row.get("team"), dict) else {}
        ref = str(team.get("$ref") or "")
        match = _TEAM_ID.search(ref)
        if match:
            ids.add(match.group(1))
    return ids


def _is_usable_player(row: dict[str, Any]) -> bool:
    status = row.get("status") if isinstance(row.get("status"), dict) else {}
    kind = str(status.get("type") or status.get("name") or "").strip().lower()
    if kind in {"practice-squad", "practicesquad", "suspended"}:
        return False
    injuries = row.get("injuries")
    if isinstance(injuries, list):
        for injury in injuries:
            if not isinstance(injury, dict):
                continue
            if str(injury.get("status") or "").strip().lower() == "out":
                return False
    return True


def _position_abbr(row: dict[str, Any]) -> str:
    position = row.get("position") if isinstance(row.get("position"), dict) else {}
    return _clean(position.get("abbreviation")).upper()


def _athlete_name(row: dict[str, Any]) -> str:
    return _clean(row.get("displayName") or row.get("fullName") or row.get("shortName"))


def _experience_years(row: dict[str, Any]) -> int | None:
    experience = row.get("experience")
    if isinstance(experience, dict):
        return _int_or_none(experience.get("years"))
    return _int_or_none(experience)


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
        years = int(float(value))
    except (TypeError, ValueError):
        return None
    if years < 0:
        return None
    return years


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
