"""SPA board payload: live source badge, view mode, records."""

from __future__ import annotations

from datetime import datetime, timezone

from sportswall.board import build_board
from sportswall.const import BOARD_VIEW_MULTI, UI_THEME_TEAM
from sportswall.games import Game, TeamSide


def _side(abbr: str, *, home: bool = False, record: str = "3-2") -> TeamSide:
    return TeamSide(
        abbreviation=abbr,
        name=abbr,
        nickname=abbr,
        location=abbr,
        city=abbr,
        region="XX",
        score=10,
        winner=home,
        logo_url="https://example.com/logo.png",
        color="112233",
        alt_color="445566",
        home=home,
        latitude=None,
        longitude=None,
        record=record,
    )


def test_build_board_spa_fields() -> None:
    game = Game(
        id="1",
        league="nfl",
        name="KC at DEN",
        short_name="KC@DEN",
        start=datetime(2026, 11, 1, 20, 0, tzinfo=timezone.utc),
        status="in",
        status_detail="Q3 8:12",
        period="Q3",
        clock="8:12",
        venue="Empower Field",
        venue_city="Denver",
        venue_region="CO",
        indoor=False,
        broadcasts=["CBS"],
        away=_side("KC", record="6-2"),
        home=_side("DEN", home=True, record="5-3"),
        possession="away",
        situation_text="3rd & 4 at DEN 32",
    )
    board = build_board(
        [game],
        datetime(2026, 11, 1, 21, 0, tzinfo=timezone.utc),
        ui_theme=UI_THEME_TEAM,
        board_view=BOARD_VIEW_MULTI,
        fantasy_enabled=True,
        fantasy_error="",
    )
    assert board["data_source"] == "live"
    assert board["ui_theme"] == UI_THEME_TEAM
    assert board["board_view"] == BOARD_VIEW_MULTI
    assert board["fantasy_enabled"] is True
    featured = board["featured"]
    assert featured is not None
    assert featured["situation"] == "3rd & 4 at DEN 32"
    assert featured["possession"] == "away"
    assert featured["away_record"] == "6-2"
    assert featured["home_record"] == "5-3"
    assert featured["away"]["color"] == "112233"


def test_possession_maps_from_espn_team_id() -> None:
    from sportswall.espn import _possession_side, _situation_text

    away = _side("CHI")
    away.espn_id = "3"
    home = _side("SEA", home=True)
    home.espn_id = "26"
    situation = {
        "possession": "26",
        "downDistanceText": "2nd & 18 at CHI 21",
    }
    assert _possession_side(situation, away, home) == "home"
    assert _situation_text(situation) == "2nd & 18 at CHI 21"
    assert _possession_side({"possession": "3"}, away, home) == "away"
    assert _possession_side({}, away, home) == ""
