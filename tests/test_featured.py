"""Featured game pin + leaders/fantasy board fields."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sportswall.board import build_board, resolve_featured
from sportswall.fantasy_espn import players_in_game
from sportswall.games import Game, TeamSide
from sportswall.leaders import parse_leaders
from sportswall.odds import parse_odds

FIXTURES = Path(__file__).parent / "fixtures"


def _side(abbr: str, home: bool = False) -> TeamSide:
    return TeamSide(
        abbreviation=abbr,
        name=abbr,
        nickname=abbr,
        location=abbr,
        city=abbr,
        region="XX",
        score=7 if not home else 14,
        winner=home,
        logo_url="",
        color="112233",
        alt_color="445566",
        home=home,
        latitude=None,
        longitude=None,
    )


def _game(
    game_id: str,
    league: str,
    status: str,
    away: str,
    home: str,
    hour: int = 20,
) -> Game:
    return Game(
        id=game_id,
        league=league,
        name=f"{away} at {home}",
        short_name=f"{away}@{home}",
        start=datetime(2026, 11, 1, hour, 0, tzinfo=timezone.utc),
        status=status,
        status_detail="live" if status == "in" else status,
        period="Q2",
        clock="5:00",
        venue="Test Stadium",
        venue_city="Testville",
        venue_region="TS",
        indoor=False,
        broadcasts=["CBS"],
        away=_side(away, home=False),
        home=_side(home, home=True),
    )


def test_resolve_featured_prefers_pin() -> None:
    live_early = _game("1", "nfl", "in", "KC", "BUF", hour=17)
    live_late = _game("2", "nfl", "in", "PHI", "DAL", hour=20)
    games = [live_early, live_late]
    assert resolve_featured(games).id == "2"
    assert resolve_featured(games, "1").id == "1"


def test_resolve_featured_ignores_missing_pin() -> None:
    game = _game("9", "nba", "pre", "BOS", "NYK")
    assert resolve_featured([game], "missing").id == "9"


def test_build_board_attaches_leaders_and_fantasy() -> None:
    game = _game("1", "nfl", "in", "PHI", "DAL")
    board = build_board(
        [game],
        datetime(2026, 11, 1, 18, 0, tzinfo=timezone.utc),
        featured_game_id="1",
        leaders=[{"line": "PHI J. Hurts · Passing Yards · 152"}],
        odds={
            "provider": "Draft Kings",
            "spread": "SEA -3",
            "over_under": "O/U 46.5",
            "away_ml": "+140",
            "home_ml": "-166",
            "line": "SEA -3 · O/U 46.5 · ML +140 / -166",
        },
        fantasy_players=[{"line": "QB J. Hurts (PHI) 18.4"}],
    )
    featured = board["featured"]
    assert featured["pinned"] is True
    assert featured["leaders"][0]["line"].startswith("PHI")
    assert featured["odds"]["line"].startswith("SEA -3")
    assert "YOUR" not in featured["fantasy_players"][0]["line"]
    assert "J. Hurts" in board["md_fantasy"]
    assert "Passing" in board["md_leaders"]


def test_parse_odds_prefers_priority_provider() -> None:
    import json

    payload = {"pickcenter": json.loads((FIXTURES / "summary_odds_nfl.json").read_text())}
    odds = parse_odds(payload)
    assert odds is not None
    assert odds["provider"] == "Draft Kings"
    assert odds["spread"] == "SEA -3"
    assert odds["over_under"] == "O/U 46.5"
    assert odds["away_ml"] == "+140"
    assert odds["home_ml"] == "-166"
    assert "SEA -3" in odds["line"]
    assert "O/U 46.5" in odds["line"]


def test_parse_leaders_prefers_skill_categories() -> None:
    import json

    payload = {"leaders": json.loads((FIXTURES / "summary_leaders_nfl.json").read_text())}
    rows = parse_leaders(payload, "nfl")
    assert rows
    assert any(row["category"] == "Passing Yards" for row in rows)
    assert len(rows) <= 6


def test_fantasy_players_in_featured_game_only() -> None:
    payload = {
        "teams": [
            {
                "id": 3,
                "roster": {
                    "entries": [
                        {
                            "lineupSlotId": 0,
                            "playerPoolEntry": {
                                "appliedStatTotal": 18.4,
                                "player": {
                                    "fullName": "Jalen Hurts",
                                    "defaultPositionId": 1,
                                    "proTeamId": 21,
                                },
                            },
                        },
                        {
                            "lineupSlotId": 20,
                            "playerPoolEntry": {
                                "appliedStatTotal": 12.0,
                                "player": {
                                    "fullName": "Bench Guy",
                                    "defaultPositionId": 2,
                                    "proTeamId": 21,
                                },
                            },
                        },
                        {
                            "lineupSlotId": 2,
                            "playerPoolEntry": {
                                "appliedStatTotal": 9.1,
                                "player": {
                                    "fullName": "Other Team RB",
                                    "defaultPositionId": 2,
                                    "proTeamId": 12,
                                },
                            },
                        },
                    ]
                },
            }
        ]
    }
    players = players_in_game(payload, team_id=3, away_abbr="PHI", home_abbr="DAL")
    assert len(players) == 1
    assert players[0]["name"] == "Jalen Hurts"
    assert players[0]["team"] == "PHI"
    assert players[0]["points"] == 18.4
