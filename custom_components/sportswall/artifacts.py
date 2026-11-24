"""Featured-game Art'ifacts — extensible fact chips under the matchup."""

from __future__ import annotations

from typing import Any

from .const import UNIT_IMPERIAL
from .roster_facts import oline_chip_value

# Group title on the board (honorific spelling).
ARTIFACTS_TITLE = "Art'ifacts"

# Stable keys so future facts can be added without renaming old ones.
KEY_TV = "tv"
KEY_WEATHER = "weather"
KEY_VENUE = "venue"
KEY_SURFACE = "surface"
KEY_TRAVEL = "distance"
KEY_ELEVATION = "elevation"
KEY_AWAY_COACH = "away_coach"
KEY_HOME_COACH = "home_coach"
KEY_AWAY_OLINE = "away_oline"
KEY_HOME_OLINE = "home_oline"
KEY_AWAY_QB = "away_qb"
KEY_HOME_QB = "home_qb"


def build_artifacts(card: dict[str, Any], units: str = UNIT_IMPERIAL) -> list[dict[str, str]]:
    """Return ordered Art'ifact chips for a board card."""
    items: list[dict[str, str]] = []

    network = str(card.get("network") or "").strip()
    if network and network != "TBD":
        items.append(_chip(KEY_TV, "TV", network))

    weather = str(card.get("weather_line") or "").strip()
    if not weather and card.get("indoor"):
        weather = "Indoor"
    if weather:
        items.append(_chip(KEY_WEATHER, "Weather", weather))

    venue = str(card.get("venue") or card.get("venue_label") or "").strip()
    if venue and venue != "TBD":
        items.append(_chip(KEY_VENUE, "Venue", venue))

    surface = str(card.get("surface") or "").strip()
    if surface:
        items.append(_chip(KEY_SURFACE, "Surface", surface))

    distance = str(card.get("travel_label") or "").strip()
    if distance:
        items.append(_chip(KEY_TRAVEL, "Distance", distance))

    elevation = elevation_label(card.get("elevation_m"), units)
    if elevation:
        items.append(_chip(KEY_ELEVATION, "Elevation", elevation))

    away = card.get("away") if isinstance(card.get("away"), dict) else {}
    home = card.get("home") if isinstance(card.get("home"), dict) else {}
    away_abbr = str(away.get("abbreviation") or "Away").strip() or "Away"
    home_abbr = str(home.get("abbreviation") or "Home").strip() or "Home"

    away_coach = str(away.get("coach_label") or "").strip()
    home_coach = str(home.get("coach_label") or "").strip()
    if away_coach:
        items.append(_chip(KEY_AWAY_COACH, f"{away_abbr} HC", away_coach))
    if home_coach:
        items.append(_chip(KEY_HOME_COACH, f"{home_abbr} HC", home_coach))

    away_oline = oline_chip_value(away.get("oline_avg_lb"), units)
    home_oline = oline_chip_value(home.get("oline_avg_lb"), units)
    if away_oline:
        items.append(_chip(KEY_AWAY_OLINE, f"{away_abbr} OL", away_oline))
    if home_oline:
        items.append(_chip(KEY_HOME_OLINE, f"{home_abbr} OL", home_oline))

    away_qb = str(away.get("qb_label") or "").strip()
    home_qb = str(home.get("qb_label") or "").strip()
    if away_qb:
        items.append(_chip(KEY_AWAY_QB, f"{away_abbr} QB", away_qb))
    if home_qb:
        items.append(_chip(KEY_HOME_QB, f"{home_abbr} QB", home_qb))

    return items


def elevation_label(elevation_m: object, units: str = UNIT_IMPERIAL) -> str:
    try:
        meters = float(elevation_m)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if units == UNIT_IMPERIAL:
        feet = meters * 3.280839895
        return f"{feet:,.0f} ft"
    return f"{meters:,.0f} m"


def artifacts_markdown(artifacts: list[dict[str, str]]) -> str:
    if not artifacts:
        return ""
    body = " · ".join(
        f"{item['label']}: {item['value']}" for item in artifacts if item.get("value")
    )
    return f"{ARTIFACTS_TITLE} · {body}" if body else ""


def _chip(key: str, label: str, value: str) -> dict[str, str]:
    return {"key": key, "label": label, "value": value}
