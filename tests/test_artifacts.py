"""Art'ifacts grouping and elevation labels."""

from __future__ import annotations

from sportswall.artifacts import ARTIFACTS_TITLE, build_artifacts, elevation_label
from sportswall.weather import normalize_condition


def test_build_artifacts_includes_elevation() -> None:
    card = {
        "network": "NBC",
        "weather_line": "72°F · Clear",
        "venue": "Empower Field",
        "surface": "Grass",
        "travel_label": "1,800 mi",
        "cities_route": "Kansas City → Denver",
        "elevation_m": 1610,
    }
    items = build_artifacts(card, units="imperial")
    keys = [item["key"] for item in items]
    assert keys == ["tv", "weather", "venue", "surface", "distance", "elevation"]
    assert items[3]["label"] == "Surface"
    assert items[3]["value"] == "Grass"
    assert items[4]["label"] == "Distance"
    assert items[4]["value"] == "1,800 mi"
    assert items[-1]["label"] == "Elevation"
    assert items[-1]["value"] == "5,282 ft"
    assert ARTIFACTS_TITLE == "Art'ifacts"


def test_build_artifacts_includes_qb_and_oline() -> None:
    card = {
        "away": {
            "abbreviation": "CIN",
            "qb_label": "Joe Burrow · 6 yrs",
            "oline_avg_lb": 312.2,
        },
        "home": {
            "abbreviation": "WSH",
            "qb_label": "Jayden Daniels · 3 yrs",
            "oline_avg_lb": 318.0,
        },
    }
    items = build_artifacts(card, units="imperial")
    values = {item["label"]: item["value"] for item in items}
    assert values["CIN OL"] == "312 lb avg"
    assert values["WSH OL"] == "318 lb avg"
    assert values["CIN QB"] == "Joe Burrow · 6 yrs"
    assert values["WSH QB"] == "Jayden Daniels · 3 yrs"


def test_elevation_metric() -> None:
    assert elevation_label(1610, "metric") == "1,610 m"


def test_normalize_accuweather_shower() -> None:
    assert normalize_condition("A shower") == "Showers"
    assert normalize_condition("mostly sunny") == "Mostly sunny"


def test_weather_line_uses_dot_separator() -> None:
    from sportswall.board import _weather_line

    assert _weather_line({"temp_label": "55°F", "weather_text": "Showers"}) == "55°F · Showers"
