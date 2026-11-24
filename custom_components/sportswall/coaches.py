"""Parse ESPN team roster head-coach fields."""

from __future__ import annotations

import re
from typing import Any

_SEASON_YEAR = re.compile(r"/seasons/(\d{4})/")


def parse_head_coach(payload: dict[str, Any] | None) -> tuple[str, int | None, str]:
    """Return (display name, experience years, coach id) from an ESPN roster payload."""
    if not isinstance(payload, dict):
        return "", None, ""
    coaches = payload.get("coach")
    if not isinstance(coaches, list) or not coaches:
        return "", None, ""
    first = coaches[0]
    if not isinstance(first, dict):
        return "", None, ""
    name = _coach_name(first)
    years = _years(first.get("experience"))
    return name, years, _clean(first.get("id"))


def tenure_years_from_person(payload: dict[str, Any] | None) -> int | None:
    """College rosters omit experience; count unique coachSeasons instead."""
    if not isinstance(payload, dict):
        return None
    seasons = payload.get("coachSeasons")
    if not isinstance(seasons, list) or not seasons:
        return None
    years: set[int] = set()
    for row in seasons:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("$ref") or "")
        match = _SEASON_YEAR.search(ref)
        if match:
            years.add(int(match.group(1)))
    if not years:
        return len(seasons) or None
    return len(years)


def coach_chip_value(name: str, years: int | None) -> str:
    clean = (name or "").strip()
    if not clean:
        return ""
    if years is None:
        return clean
    unit = "yr" if years == 1 else "yrs"
    return f"{clean} · {years} {unit}"


def _coach_name(row: dict[str, Any]) -> str:
    first = _clean(row.get("firstName"))
    last = _clean(row.get("lastName"))
    full = " ".join(part for part in (first, last) if part).strip()
    if full:
        return full
    return _clean(row.get("displayName") or row.get("name"))


def _years(value: Any) -> int | None:
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
