"""Constants for Sports Wall."""

from datetime import timedelta

DOMAIN = "sportswall"

CONF_TV_ENABLED = "tv_enabled"
CONF_TV_POWER = "tv_power"
CONF_TV_PLAYER = "tv_player"
CONF_UNITS = "units"
CONF_THEME = "theme"
CONF_UI_THEME = "ui_theme"
CONF_BOARD_VIEW = "board_view"
CONF_DISPLAY_MODE = "display_mode"
CONF_TIME_FORMAT = "time_format"
CONF_SHOW_LOGOS = "show_logos"
CONF_QUIET_ENABLED = "quiet_enabled"
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"
CONF_REFRESH_SECONDS = "refresh_seconds"
CONF_LEAGUES = "leagues"
CONF_SCOPE = "scope"
CONF_FANTASY_ENABLED = "fantasy_enabled"
CONF_FANTASY_LEAGUE_ID = "fantasy_league_id"
CONF_FANTASY_TEAM_ID = "fantasy_team_id"
CONF_FANTASY_ESPN_S2 = "fantasy_espn_s2"
CONF_FANTASY_SWID = "fantasy_swid"
CONF_FANTASY_SEASON = "fantasy_season"

FEATURED_AUTO = "auto"
SERVICE_SELECT_GAME = "select_game"
ATTR_GAME_ID = "game_id"
ATTR_AUTO = "auto"

UNIT_IMPERIAL = "imperial"
UNIT_METRIC = "metric"
DEFAULT_UNITS = UNIT_IMPERIAL

STYLE_ARENA = "arena"
STYLE_BROADCAST = "broadcast"
STYLE_NIGHT = "night"
STYLE_DAYLIGHT = "daylight"
DEFAULT_THEME = STYLE_ARENA

# SPA chrome themes (Team / Stadium are UI-only; PNG Cast uses STYLE_*).
UI_THEME_NIGHT = "night"
UI_THEME_DAYLIGHT = "daylight"
UI_THEME_TEAM = "team"
UI_THEME_STADIUM = "stadium"
UI_THEME_ARENA = "arena"
UI_THEME_BROADCAST = "broadcast"
DEFAULT_UI_THEME = UI_THEME_NIGHT
UI_THEMES = {
    UI_THEME_NIGHT,
    UI_THEME_DAYLIGHT,
    UI_THEME_TEAM,
    UI_THEME_STADIUM,
    UI_THEME_ARENA,
    UI_THEME_BROADCAST,
}
UI_THEME_TO_STYLE = {
    UI_THEME_NIGHT: STYLE_NIGHT,
    UI_THEME_DAYLIGHT: STYLE_DAYLIGHT,
    UI_THEME_TEAM: STYLE_ARENA,
    UI_THEME_STADIUM: STYLE_NIGHT,
    UI_THEME_ARENA: STYLE_ARENA,
    UI_THEME_BROADCAST: STYLE_BROADCAST,
}

BOARD_VIEW_GAME = "game"
BOARD_VIEW_MULTI = "multi"
BOARD_VIEW_FANTASY = "fantasy"
BOARD_VIEW_AMBIENT = "ambient"
DEFAULT_BOARD_VIEW = BOARD_VIEW_GAME
BOARD_VIEWS = {
    BOARD_VIEW_GAME,
    BOARD_VIEW_MULTI,
    BOARD_VIEW_FANTASY,
    BOARD_VIEW_AMBIENT,
}
BOARD_VIEW_LABELS = {
    BOARD_VIEW_GAME: "Game Focus",
    BOARD_VIEW_MULTI: "Multiview",
    BOARD_VIEW_FANTASY: "Fantasy HQ",
    BOARD_VIEW_AMBIENT: "Ambient",
}

TIME_FOLLOW_UNITS = "follow_units"
TIME_12H = "12h"
TIME_24H = "24h"
DEFAULT_TIME_FORMAT = TIME_FOLLOW_UNITS
DEFAULT_SHOW_LOGOS = True
DEFAULT_QUIET_ENABLED = False
DEFAULT_QUIET_START = "22:00:00"
DEFAULT_QUIET_END = "07:00:00"
DEFAULT_REFRESH_SECONDS = 120
# While any game is live, poll ESPN this often (Cast/idle still use refresh_seconds).
LIVE_REFRESH_SECONDS = 10
# Timer fires this often; _poll_due decides whether a real ESPN fetch runs.
POLL_TICK_SECONDS = 5
# Leaders / odds / fantasy can lag scoreboard a bit — keep score path snappy.
FEATURED_ENRICH_SECONDS = 30
MIN_REFRESH_SECONDS = 10
MAX_REFRESH_SECONDS = 300

DISPLAY_IMAGE = "image"
DISPLAY_LIVE = "live"
DEFAULT_DISPLAY_MODE = DISPLAY_IMAGE

SCOPE_TODAY = "today"
SCOPE_SLATE = "slate"
DEFAULT_SCOPE = SCOPE_TODAY

LEAGUE_NFL = "nfl"
LEAGUE_NBA = "nba"
LEAGUE_MLB = "mlb"
LEAGUE_NHL = "nhl"
LEAGUE_NCAAF = "ncaaf"
LEAGUE_NCAAB = "ncaab"

DEFAULT_LEAGUES = [LEAGUE_NFL, LEAGUE_NBA, LEAGUE_MLB, LEAGUE_NHL, LEAGUE_NCAAF]
ALL_LEAGUES = [
    LEAGUE_NFL,
    LEAGUE_NBA,
    LEAGUE_MLB,
    LEAGUE_NHL,
    LEAGUE_NCAAF,
    LEAGUE_NCAAB,
]

LEAGUE_LABELS = {
    LEAGUE_NFL: "NFL",
    LEAGUE_NBA: "NBA",
    LEAGUE_MLB: "MLB",
    LEAGUE_NHL: "NHL",
    LEAGUE_NCAAF: "College football",
    LEAGUE_NCAAB: "College basketball",
}

THEME_HA = {
    STYLE_ARENA: "sportswall",
    STYLE_BROADCAST: "sportswall-broadcast",
    STYLE_NIGHT: "sportswall-night",
    STYLE_DAYLIGHT: "sportswall-daylight",
}

TV_POWER_ON_DELAY = timedelta(seconds=10)
TV_CAST_SOURCE = "Cast"
TV_CAST_SOURCES = frozenset({"cast", "chromecast", "google cast"})
TV_TAKEOVER_REASONS = frozenset({"tv_on", "armed"})
SERVICE_RECAST = "recast"
BOARD_PNG_NAME = "sportswall-board.png"

DASHBOARD_PATH = "sports-wall"
VIEW_PATH = "board"

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
)
ESPN_SUMMARY = (
    "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary"
)
ESPN_FANTASY_LEAGUE = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/"
    "{season}/segments/0/leagues/{league_id}"
)
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_ELEVATION = "https://api.open-meteo.com/v1/elevation"

DEFAULT_FANTASY_ENABLED = False


def keepalive_interval(seconds: object = None) -> timedelta:
    """Clamp the configured idle refresh interval."""
    return timedelta(
        seconds=_clamp_seconds(
            seconds, DEFAULT_REFRESH_SECONDS, MIN_REFRESH_SECONDS, MAX_REFRESH_SECONDS
        )
    )


def poll_tick_interval() -> timedelta:
    """Base timer tick — short enough to catch live scoring."""
    return timedelta(seconds=POLL_TICK_SECONDS)


def _clamp_seconds(
    seconds: object,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float, str)):
        value = default
    else:
        try:
            value = int(round(float(seconds)))
        except (TypeError, ValueError):
            value = default
    return max(minimum, min(maximum, value))
