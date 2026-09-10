"""Constants for Sports Wall."""

from datetime import timedelta

DOMAIN = "sportswall"

CONF_TV_ENABLED = "tv_enabled"
CONF_TV_POWER = "tv_power"
CONF_TV_PLAYER = "tv_player"
CONF_UNITS = "units"
CONF_THEME = "theme"
CONF_DISPLAY_MODE = "display_mode"
CONF_TIME_FORMAT = "time_format"
CONF_SHOW_LOGOS = "show_logos"
CONF_QUIET_ENABLED = "quiet_enabled"
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"
CONF_REFRESH_SECONDS = "refresh_seconds"
CONF_LEAGUES = "leagues"
CONF_SCOPE = "scope"

UNIT_IMPERIAL = "imperial"
UNIT_METRIC = "metric"
DEFAULT_UNITS = UNIT_IMPERIAL

STYLE_ARENA = "arena"
STYLE_BROADCAST = "broadcast"
STYLE_NIGHT = "night"
STYLE_DAYLIGHT = "daylight"
DEFAULT_THEME = STYLE_ARENA

TIME_FOLLOW_UNITS = "follow_units"
TIME_12H = "12h"
TIME_24H = "24h"
DEFAULT_TIME_FORMAT = TIME_FOLLOW_UNITS
DEFAULT_SHOW_LOGOS = True
DEFAULT_QUIET_ENABLED = False
DEFAULT_QUIET_START = "22:00:00"
DEFAULT_QUIET_END = "07:00:00"
DEFAULT_REFRESH_SECONDS = 120
MIN_REFRESH_SECONDS = 15
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

DEFAULT_LEAGUES = [LEAGUE_NFL, LEAGUE_NBA, LEAGUE_MLB, LEAGUE_NHL]
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
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"


def keepalive_interval(seconds: object = None) -> timedelta:
    """Clamp the image refresh to a usable Cast interval."""
    return timedelta(
        seconds=_clamp_seconds(
            seconds, DEFAULT_REFRESH_SECONDS, MIN_REFRESH_SECONDS, MAX_REFRESH_SECONDS
        )
    )


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
