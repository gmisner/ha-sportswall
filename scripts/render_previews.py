"""Render README TV-theme previews without Home Assistant."""

from __future__ import annotations

import sys
import types
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "sportswall"
pkg = types.ModuleType("sportswall")
pkg.__path__ = [str(PKG)]
pkg.__package__ = "sportswall"
sys.modules["sportswall"] = pkg

from sportswall.board_image import render_board_png  # noqa: E402
from sportswall.const import (  # noqa: E402
    LEAGUE_MLB,
    LEAGUE_NFL,
    STYLE_ARENA,
    STYLE_BROADCAST,
    STYLE_DAYLIGHT,
    STYLE_NIGHT,
)
from sportswall.espn import parse_scoreboard  # noqa: E402

from zoneinfo import ZoneInfo

NOW = datetime(2026, 9, 9, 16, 45, tzinfo=ZoneInfo("America/New_York"))
OUT = ROOT / "docs" / "images"


def _games():
    nfl = {
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
                                    "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/scoreboard/sea.png",
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
                                    "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/scoreboard/ne.png",
                                },
                            },
                        ],
                    }
                ],
            }
        ]
    }
    mlb = {
        "events": [
            {
                "id": "2",
                "date": "2026-09-09T17:10Z",
                "name": "Minnesota Twins at Detroit Tigers",
                "shortName": "MIN @ DET",
                "weather": {"displayValue": "Cloudy", "temperature": 74},
                "status": {
                    "type": {"state": "in", "shortDetail": "Top 3rd"},
                    "displayClock": "0:00",
                    "period": 3,
                },
                "competitions": [
                    {
                        "venue": {
                            "fullName": "Comerica Park",
                            "address": {"city": "Detroit", "state": "Michigan"},
                        },
                        "broadcasts": [{"market": "national", "names": ["MLB.TV"]}],
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
                                    "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/det.png",
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
                                    "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/min.png",
                                },
                            },
                        ],
                    }
                ],
            }
        ]
    }
    return parse_scoreboard(nfl, LEAGUE_NFL) + parse_scoreboard(mlb, LEAGUE_MLB)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    games = _games()
    for style, name in (
        (STYLE_ARENA, "tv-arena.png"),
        (STYLE_BROADCAST, "tv-broadcast.png"),
        (STYLE_NIGHT, "tv-night.png"),
        (STYLE_DAYLIGHT, "tv-daylight.png"),
    ):
        raw = render_board_png(games, now=NOW, style=style, show_logos=True)
        image = Image.open(BytesIO(raw)).convert("RGB")
        image = image.resize((1280, 720), Image.Resampling.LANCZOS)
        dest = OUT / name
        image.save(dest, "PNG", optimize=True)
        print(dest, dest.stat().st_size)

    empty = render_board_png([], now=NOW, style=STYLE_ARENA, show_logos=True)
    image = Image.open(BytesIO(empty)).convert("RGB").resize((1280, 720), Image.Resampling.LANCZOS)
    dest = OUT / "tv-empty.png"
    image.save(dest, "PNG", optimize=True)
    print(dest, dest.stat().st_size)

    social = Image.open(OUT / "tv-arena.png").convert("RGB")
    social.save(OUT / "social.png", "PNG", optimize=True)
    print(OUT / "social.png")


if __name__ == "__main__":
    main()
