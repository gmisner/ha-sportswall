from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sportswall.const import LEAGUE_MLB, LEAGUE_NFL
from sportswall.distance import haversine_miles
from sportswall.espn import parse_scoreboard
from sportswall.games import Game, TeamSide, on_todays_board
from sportswall.teams import team_home


def _side(**kwargs) -> TeamSide:
    defaults = dict(
        abbreviation="NE",
        name="New England Patriots",
        nickname="Patriots",
        location="New England",
        city="New England",
        region="",
        score=None,
        winner=False,
        logo_url="",
        color="002a5c",
        alt_color="c60c30",
        home=False,
        latitude=None,
        longitude=None,
        record="0-0",
    )
    defaults.update(kwargs)
    return TeamSide(**defaults)


def test_patriots_seahawks_travel_is_coast_to_coast() -> None:
    away = team_home(LEAGUE_NFL, "NE")
    home = team_home(LEAGUE_NFL, "SEA")
    assert away is not None and home is not None
    miles = haversine_miles(away.latitude, away.longitude, home.latitude, home.longitude)
    assert 2400 < miles < 2600


def test_shared_stadium_is_local() -> None:
    giants = team_home(LEAGUE_NFL, "NYG")
    jets = team_home(LEAGUE_NFL, "NYJ")
    assert giants is not None and jets is not None
    miles = haversine_miles(giants.latitude, giants.longitude, jets.latitude, jets.longitude)
    assert miles < 1
    game = Game(
        id="1",
        league=LEAGUE_NFL,
        name="Jets at Giants",
        short_name="NYJ @ NYG",
        start=datetime(2026, 9, 9, tzinfo=UTC),
        status="pre",
        status_detail="Sun",
        period="",
        clock="",
        venue="MetLife Stadium",
        venue_city="East Rutherford",
        venue_region="NJ",
        indoor=False,
        broadcasts=["CBS"],
        away=_side(abbreviation="NYJ", location="New York", home=False),
        home=_side(abbreviation="NYG", location="New York", home=True, color="0b2265"),
    )
    game.apply_homes()
    assert game.travel_label() == "Local"


def test_parse_nfl_scoreboard_fixture() -> None:
    payload = {
        "events": [
            {
                "id": "401772510",
                "date": "2026-09-10T00:20Z",
                "name": "New England Patriots at Seattle Seahawks",
                "shortName": "NE @ SEA",
                "weather": {"displayValue": "Mostly sunny", "temperature": 75},
                "status": {
                    "displayClock": "0:00",
                    "period": 0,
                    "type": {
                        "state": "pre",
                        "shortDetail": "9/9 - 8:20 PM EDT",
                        "description": "Scheduled",
                    },
                },
                "competitions": [
                    {
                        "venue": {
                            "fullName": "Lumen Field",
                            "indoor": False,
                            "address": {"city": "Seattle", "state": "WA"},
                        },
                        "broadcasts": [{"market": "national", "names": ["NBC"]}],
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": "0",
                                "winner": False,
                                "records": [{"type": "total", "summary": "0-0"}],
                                "team": {
                                    "abbreviation": "SEA",
                                    "displayName": "Seattle Seahawks",
                                    "shortDisplayName": "Seahawks",
                                    "location": "Seattle",
                                    "name": "Seahawks",
                                    "color": "002a5c",
                                    "alternateColor": "69be28",
                                    "logo": "https://example.test/sea.png",
                                },
                            },
                            {
                                "homeAway": "away",
                                "score": "0",
                                "winner": False,
                                "records": [{"type": "total", "summary": "0-0"}],
                                "team": {
                                    "abbreviation": "NE",
                                    "displayName": "New England Patriots",
                                    "shortDisplayName": "Patriots",
                                    "location": "New England",
                                    "name": "Patriots",
                                    "color": "002a5c",
                                    "alternateColor": "c60c30",
                                    "logo": "https://example.test/ne.png",
                                },
                            },
                        ],
                    }
                ],
            }
        ]
    }
    games = parse_scoreboard(payload, LEAGUE_NFL)
    assert len(games) == 1
    game = games[0]
    assert game.network == "NBC"
    assert game.venue_city == "Seattle"
    assert game.weather_text == "Mostly sunny"
    assert game.weather_temp_f == 75
    assert game.away is not None and game.home is not None
    assert game.away.city == "Foxborough"
    assert game.home.city == "Seattle"
    assert game.travel_miles is not None and game.travel_miles > 2400
    assert "Foxborough" in game.cities_route()


def test_live_mlb_scores_and_broadcasts() -> None:
    payload = {
        "events": [
            {
                "id": "2",
                "date": "2026-09-09T17:10Z",
                "name": "Minnesota Twins at Detroit Tigers",
                "shortName": "MIN @ DET",
                "status": {
                    "displayClock": "0:00",
                    "period": 3,
                    "type": {"state": "in", "shortDetail": "Top 3rd", "description": "In Progress"},
                },
                "competitions": [
                    {
                        "venue": {
                            "fullName": "Comerica Park",
                            "address": {"city": "Detroit", "state": "Michigan"},
                        },
                        "broadcasts": [
                            {"market": "national", "names": ["MLB.TV"]},
                            {"market": "home", "names": ["Tigers.TV"]},
                        ],
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": "4",
                                "team": {
                                    "abbreviation": "DET",
                                    "displayName": "Detroit Tigers",
                                    "shortDisplayName": "Tigers",
                                    "location": "Detroit",
                                    "color": "0c2340",
                                    "alternateColor": "fa4616",
                                    "logo": "",
                                },
                            },
                            {
                                "homeAway": "away",
                                "score": "2",
                                "team": {
                                    "abbreviation": "MIN",
                                    "displayName": "Minnesota Twins",
                                    "shortDisplayName": "Twins",
                                    "location": "Minnesota",
                                    "color": "002b5c",
                                    "alternateColor": "d31145",
                                    "logo": "",
                                },
                            },
                        ],
                    }
                ],
            }
        ]
    }
    game = parse_scoreboard(payload, LEAGUE_MLB)[0]
    assert game.is_live
    assert game.network == "MLB.TV"
    assert game.away is not None and game.away.score == 2
    assert game.home is not None and game.home.score == 4


def test_todays_board_keeps_live_games_from_next_utc_day() -> None:
    now = datetime(2026, 9, 9, 17, 30, tzinfo=UTC)
    live = Game(
        id="live",
        league=LEAGUE_NFL,
        name="Patriots at Seahawks",
        short_name="NE @ SEA",
        start=datetime(2026, 9, 10, 0, 20, tzinfo=UTC),
        status="in",
        status_detail="1st",
        period="1st",
        clock="1:22",
        venue="Lumen Field",
        venue_city="Seattle",
        venue_region="WA",
        indoor=False,
        away=_side(),
        home=_side(abbreviation="SEA", home=True),
    )
    later = Game(
        id="later",
        league=LEAGUE_NFL,
        name="49ers vs Rams",
        short_name="SF VS LAR",
        start=datetime(2026, 9, 11, 0, 35, tzinfo=UTC),
        status="pre",
        status_detail="Thu",
        period="",
        clock="",
        venue="Sao Paulo",
        venue_city="Sao Paulo",
        venue_region="",
        indoor=False,
        away=_side(abbreviation="SF"),
        home=_side(abbreviation="LAR", home=True),
    )
    assert on_todays_board(live, now)
    assert not on_todays_board(later, now)


def test_fonts_ship_with_the_integration() -> None:
    fonts = Path(__file__).resolve().parents[1] / "custom_components" / "sportswall" / "fonts"
    assert (fonts / "Roboto-Bold.ttf").is_file()
