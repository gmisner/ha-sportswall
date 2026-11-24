"""Head coach parsing and Art'ifact chips."""

from __future__ import annotations

from sportswall.artifacts import build_artifacts
from sportswall.coaches import coach_chip_value, parse_head_coach
from sportswall.games import TeamSide


def test_parse_head_coach() -> None:
    name, years, coach_id = parse_head_coach(
        {"coach": [{"id": "1", "firstName": "Nick", "lastName": "Sirianni", "experience": 5}]}
    )
    assert name == "Nick Sirianni"
    assert years == 5
    assert coach_id == "1"
    assert coach_chip_value(name, years) == "Nick Sirianni · 5 yrs"


def test_parse_head_coach_without_experience() -> None:
    name, years, coach_id = parse_head_coach(
        {"coach": [{"id": "9", "firstName": "Marco", "lastName": "Sturm"}]}
    )
    assert name == "Marco Sturm"
    assert years is None
    assert coach_id == "9"
    assert coach_chip_value(name, years) == "Marco Sturm"


def test_tenure_from_college_coach_seasons() -> None:
    from sportswall.coaches import tenure_years_from_person

    years = tenure_years_from_person(
        {
            "coachSeasons": [
                {
                    "$ref": "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2022/coaches/1"
                },
                {
                    "$ref": "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/coaches/1"
                },
                {
                    "$ref": "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2024/coaches/1"
                },
            ]
        }
    )
    assert years == 3


def test_artifacts_include_coaches() -> None:
    away = TeamSide(
        abbreviation="PHI",
        name="Eagles",
        nickname="Eagles",
        location="Philadelphia",
        city="Philadelphia",
        region="PA",
        score=7,
        winner=False,
        logo_url="",
        color="004c54",
        alt_color="a5acaf",
        home=False,
        latitude=None,
        longitude=None,
        coach_name="Nick Sirianni",
        coach_years=5,
    )
    home = TeamSide(
        abbreviation="WSH",
        name="Commanders",
        nickname="Commanders",
        location="Washington",
        city="Washington",
        region="DC",
        score=14,
        winner=True,
        logo_url="",
        color="5a1414",
        alt_color="ffb612",
        home=True,
        latitude=None,
        longitude=None,
        coach_name="Dan Quinn",
        coach_years=8,
    )
    card = {
        "network": "NBC",
        "away": away.as_dict(),
        "home": home.as_dict(),
    }
    items = build_artifacts(card)
    labels = [item["label"] for item in items]
    assert "PHI HC" in labels
    assert "WSH HC" in labels
    values = {item["label"]: item["value"] for item in items}
    assert values["PHI HC"] == "Nick Sirianni · 5 yrs"
    assert values["WSH HC"] == "Dan Quinn · 8 yrs"
