"""QB / O-line roster parsing for Art'ifacts."""

from __future__ import annotations

from sportswall.roster_facts import (
    average_oline_weight_lb,
    oline_chip_value,
    oline_depth_ids,
    parse_roster_athletes,
    qb_chip_value,
    starter_qb,
    tenure_years_from_statisticslog,
)


def _athlete(name: str, pos: str, weight: float, *, athlete_id: str = "1", years: int = 2):
    return {
        "id": athlete_id,
        "displayName": name,
        "weight": weight,
        "position": {"abbreviation": pos},
        "experience": {"years": years},
        "status": {"type": "active"},
    }


def test_average_oline_weight_from_roster_positions() -> None:
    athletes = [
        _athlete("LT", "OT", 310, athlete_id="1"),
        _athlete("LG", "G", 320, athlete_id="2"),
        _athlete("C", "C", 300, athlete_id="3"),
        _athlete("QB", "QB", 220, athlete_id="4"),
        _athlete("WR", "WR", 195, athlete_id="5"),
    ]
    assert average_oline_weight_lb(athletes) == 310.0


def test_average_oline_prefers_depth_starters() -> None:
    athletes = [
        _athlete("Starter", "OT", 300, athlete_id="10"),
        _athlete("Backup", "OT", 350, athlete_id="11"),
        _athlete("Guard", "G", 310, athlete_id="12"),
    ]
    avg = average_oline_weight_lb(athletes, {"10", "12"})
    assert avg == 305.0


def test_starter_qb_from_depth_chart() -> None:
    athletes = [
        _athlete("Backup", "QB", 210, athlete_id="2", years=10),
        _athlete("Starter", "QB", 220, athlete_id="1", years=3),
    ]
    depth = {
        "depthchart": [
            {
                "name": "Offense",
                "positions": {
                    "qb": {"athletes": [{"id": "1", "displayName": "Starter"}]},
                    "lt": {"athletes": [{"id": "10"}]},
                },
            }
        ]
    }
    assert oline_depth_ids(depth) == {"10"}
    qb_id, name, years = starter_qb(athletes, depth)
    assert qb_id == "1"
    assert name == "Starter"
    assert years == 3


def test_starter_qb_falls_back_to_experience() -> None:
    athletes = parse_roster_athletes(
        {
            "athletes": [
                {
                    "position": "offense",
                    "items": [
                        _athlete("Young", "QB", 200, athlete_id="1", years=1),
                        _athlete("Vet", "QB", 220, athlete_id="2", years=5),
                    ],
                }
            ]
        }
    )
    qb_id, name, years = starter_qb(athletes, None)
    assert qb_id == "2"
    assert name == "Vet"
    assert years == 5


def test_tenure_from_statisticslog() -> None:
    payload = {
        "entries": [
            {
                "statistics": [
                    {
                        "type": "team",
                        "team": {
                            "$ref": "http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2026/teams/28"
                        },
                    }
                ]
            },
            {
                "statistics": [
                    {
                        "type": "team",
                        "team": {
                            "$ref": "http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2025/teams/28"
                        },
                    }
                ]
            },
            {
                "statistics": [
                    {
                        "type": "team",
                        "team": {
                            "$ref": "http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2024/teams/21"
                        },
                    }
                ]
            },
        ]
    }
    assert tenure_years_from_statisticslog(payload, "28") == 2
    assert qb_chip_value("Jayden Daniels", 3) == "Jayden Daniels · 3 yrs"
    assert oline_chip_value(312.4) == "312 lb avg"
    assert oline_chip_value(220.0, "metric") == "100 kg avg"
