from __future__ import annotations

from datetime import UTC, datetime

from sportswall.board import DASHBOARD_MARKDOWN, build_board
from sportswall.board_image import render_board_png
from sportswall.const import LEAGUE_NFL, STYLE_ARENA, STYLE_BROADCAST, STYLE_DAYLIGHT, STYLE_NIGHT
from sportswall.espn import parse_scoreboard
from sportswall.schedule import in_quiet_hours
from sportswall.tv import (
    cast_source_name,
    is_cast_source,
    should_attempt_cast,
    should_refresh_board,
    should_select_cast,
)
from sportswall.weather import icon_from_text, parse_open_meteo


def _sample_games():
    data = {
        "events": [
            {
                "id": "1",
                "date": "2026-09-10T00:20Z",
                "name": "New England Patriots at Seattle Seahawks",
                "shortName": "NE @ SEA",
                "weather": {"displayValue": "Mostly sunny", "temperature": 75},
                "status": {
                    "type": {"state": "pre", "shortDetail": "8:20 PM EDT"},
                    "displayClock": "0:00",
                    "period": 0,
                },
                "competitions": [
                    {
                        "venue": {
                            "fullName": "Lumen Field",
                            "address": {"city": "Seattle", "state": "WA"},
                            "indoor": False,
                        },
                        "broadcasts": [{"market": "national", "names": ["NBC"]}],
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": "0",
                                "team": {
                                    "abbreviation": "SEA",
                                    "displayName": "Seattle Seahawks",
                                    "shortDisplayName": "Seahawks",
                                    "location": "Seattle",
                                    "color": "002a5c",
                                    "alternateColor": "69be28",
                                    "logo": "",
                                },
                            },
                            {
                                "homeAway": "away",
                                "score": "0",
                                "team": {
                                    "abbreviation": "NE",
                                    "displayName": "New England Patriots",
                                    "shortDisplayName": "Patriots",
                                    "location": "New England",
                                    "color": "002a5c",
                                    "alternateColor": "c60c30",
                                    "logo": "",
                                },
                            },
                        ],
                    }
                ],
            }
        ]
    }
    return parse_scoreboard(data, LEAGUE_NFL)


def test_cast_source_names() -> None:
    assert is_cast_source("Cast")
    assert is_cast_source("Chromecast")
    assert not is_cast_source("Netflix")
    assert cast_source_name(["HDMI-1", "Cast", "Netflix"]) == "Cast"
    assert cast_source_name(["SMARTCAST", "AirPlay"]) is None


def test_refresh_only_on_cast_or_unknown_source() -> None:
    assert should_refresh_board(source="Cast", showing_board=False)
    assert should_refresh_board(source="HDMI-1", showing_board=True)
    assert not should_refresh_board(source="Netflix", showing_board=False)


def test_select_cast_only_on_takeover() -> None:
    assert should_select_cast("tv_on")
    assert should_select_cast("armed")
    assert not should_select_cast("keep")
    assert should_attempt_cast(reason="keep", power_on=True, player_state="playing")
    assert not should_attempt_cast(reason="keep", power_on=True, player_state="off")


def test_quiet_hours_wraps_midnight() -> None:
    now = datetime(2026, 9, 9, 23, 0, tzinfo=UTC)
    assert in_quiet_hours(now, enabled=True, start="22:00:00", end="07:00:00")
    assert not in_quiet_hours(now, enabled=False, start="22:00:00", end="07:00:00")


def test_weather_icons() -> None:
    assert icon_from_text("Mostly sunny") == "cloud_sun"
    assert icon_from_text("Thunderstorms") == "storm"
    temp, text, icon = parse_open_meteo(
        {"current": {"temperature_2m": 68.2, "weather_code": 61}}
    )
    assert temp == 68.2
    assert icon == "rain"
    assert "rain" in text.lower()


def test_board_payload_and_png() -> None:
    games = _sample_games()
    now = datetime(2026, 9, 9, 12, 30, tzinfo=UTC)
    board = build_board(games, now)
    assert board["game_count"] == 1
    assert board["has_games"] is True
    assert board["featured"]["network"] == "NBC"
    assert board["games"][0]["network"] == "NBC"
    assert "Foxborough" in board["games"][0]["cities_route"]
    assert "NE  —  @  —  SEA" == board["md_score"]
    assert "NBC" in board["md_league"]
    assert "TV NBC" in board["md_facts"]
    assert board["md_ticker"] == ""
    raw = render_board_png(games, now=now, style=STYLE_ARENA, show_logos=False)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(raw) > 20_000


def test_all_themes_render() -> None:
    games = _sample_games()
    now = datetime(2026, 9, 9, 12, 30, tzinfo=UTC)
    for style in (STYLE_ARENA, STYLE_BROADCAST, STYLE_NIGHT, STYLE_DAYLIGHT):
        raw = render_board_png(games, now=now, style=style, show_logos=False)
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_live_dashboard_markdown_uses_board_copy() -> None:
    content = DASHBOARD_MARKDOWN.replace("__GAMES_ENTITY__", "sensor.sportswall_games")
    assert "sensor.sportswall_games" in content
    assert "__GAMES_ENTITY__" not in content
    assert "md_score" in DASHBOARD_MARKDOWN
    assert "NO GAMES TODAY" in DASHBOARD_MARKDOWN


def test_empty_board_renders() -> None:
    now = datetime(2026, 9, 9, 12, 30, tzinfo=UTC)
    board = build_board([], now)
    assert board["has_games"] is False
    assert board["md_score"] == ""
    raw = render_board_png([], now=now, show_logos=False)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
