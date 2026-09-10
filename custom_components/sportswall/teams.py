"""Home cities and stadium coordinates for travel distance."""

from __future__ import annotations

from dataclasses import dataclass

from .const import LEAGUE_MLB, LEAGUE_NBA, LEAGUE_NFL, LEAGUE_NHL


@dataclass(frozen=True)
class TeamHome:
    """Where a club actually lives, not the ESPN marketing name."""

    city: str
    region: str
    latitude: float
    longitude: float

    @property
    def label(self) -> str:
        if self.region:
            return f"{self.city}, {self.region}"
        return self.city


def _home(city: str, region: str, lat: float, lon: float) -> TeamHome:
    return TeamHome(city, region, lat, lon)


# Stadium / arena cities. Keys are (league, ESPN abbreviation).
TEAM_HOMES: dict[tuple[str, str], TeamHome] = {
    (LEAGUE_NFL, "ARI"): _home("Glendale", "AZ", 33.5276, -112.2626),
    (LEAGUE_NFL, "ATL"): _home("Atlanta", "GA", 33.7553, -84.4006),
    (LEAGUE_NFL, "BAL"): _home("Baltimore", "MD", 39.2780, -76.6227),
    (LEAGUE_NFL, "BUF"): _home("Orchard Park", "NY", 42.7738, -78.7870),
    (LEAGUE_NFL, "CAR"): _home("Charlotte", "NC", 35.2251, -80.8526),
    (LEAGUE_NFL, "CHI"): _home("Chicago", "IL", 41.8623, -87.6167),
    (LEAGUE_NFL, "CIN"): _home("Cincinnati", "OH", 39.0954, -84.5160),
    (LEAGUE_NFL, "CLE"): _home("Cleveland", "OH", 41.5061, -81.6995),
    (LEAGUE_NFL, "DAL"): _home("Arlington", "TX", 32.7473, -97.0945),
    (LEAGUE_NFL, "DEN"): _home("Denver", "CO", 39.7439, -105.0201),
    (LEAGUE_NFL, "DET"): _home("Detroit", "MI", 42.3400, -83.0456),
    (LEAGUE_NFL, "GB"): _home("Green Bay", "WI", 44.5013, -88.0622),
    (LEAGUE_NFL, "HOU"): _home("Houston", "TX", 29.6847, -95.4107),
    (LEAGUE_NFL, "IND"): _home("Indianapolis", "IN", 39.7601, -86.1639),
    (LEAGUE_NFL, "JAX"): _home("Jacksonville", "FL", 30.3239, -81.6373),
    (LEAGUE_NFL, "KC"): _home("Kansas City", "MO", 39.0489, -94.4839),
    (LEAGUE_NFL, "LV"): _home("Las Vegas", "NV", 36.0909, -115.1833),
    (LEAGUE_NFL, "LAC"): _home("Inglewood", "CA", 33.9535, -118.3390),
    (LEAGUE_NFL, "LAR"): _home("Inglewood", "CA", 33.9535, -118.3390),
    (LEAGUE_NFL, "MIA"): _home("Miami Gardens", "FL", 25.9580, -80.2389),
    (LEAGUE_NFL, "MIN"): _home("Minneapolis", "MN", 44.9738, -93.2581),
    (LEAGUE_NFL, "NE"): _home("Foxborough", "MA", 42.0909, -71.2643),
    (LEAGUE_NFL, "NO"): _home("New Orleans", "LA", 29.9511, -90.0812),
    (LEAGUE_NFL, "NYG"): _home("East Rutherford", "NJ", 40.8128, -74.0742),
    (LEAGUE_NFL, "NYJ"): _home("East Rutherford", "NJ", 40.8128, -74.0742),
    (LEAGUE_NFL, "PHI"): _home("Philadelphia", "PA", 39.9008, -75.1675),
    (LEAGUE_NFL, "PIT"): _home("Pittsburgh", "PA", 40.4468, -80.0158),
    (LEAGUE_NFL, "SF"): _home("Santa Clara", "CA", 37.4030, -121.9700),
    (LEAGUE_NFL, "SEA"): _home("Seattle", "WA", 47.5952, -122.3316),
    (LEAGUE_NFL, "TB"): _home("Tampa", "FL", 27.9759, -82.5033),
    (LEAGUE_NFL, "TEN"): _home("Nashville", "TN", 36.1665, -86.7713),
    (LEAGUE_NFL, "WSH"): _home("Landover", "MD", 38.9076, -76.8645),
    (LEAGUE_NFL, "WAS"): _home("Landover", "MD", 38.9076, -76.8645),
    (LEAGUE_NBA, "ATL"): _home("Atlanta", "GA", 33.7573, -84.3963),
    (LEAGUE_NBA, "BOS"): _home("Boston", "MA", 42.3662, -71.0621),
    (LEAGUE_NBA, "BKN"): _home("Brooklyn", "NY", 40.6826, -73.9747),
    (LEAGUE_NBA, "CHA"): _home("Charlotte", "NC", 35.2251, -80.8392),
    (LEAGUE_NBA, "CHI"): _home("Chicago", "IL", 41.8807, -87.6742),
    (LEAGUE_NBA, "CLE"): _home("Cleveland", "OH", 41.4965, -81.6882),
    (LEAGUE_NBA, "DAL"): _home("Dallas", "TX", 32.7905, -96.8103),
    (LEAGUE_NBA, "DEN"): _home("Denver", "CO", 39.7487, -105.0077),
    (LEAGUE_NBA, "DET"): _home("Detroit", "MI", 42.3410, -83.0550),
    (LEAGUE_NBA, "GS"): _home("San Francisco", "CA", 37.7680, -122.3877),
    (LEAGUE_NBA, "GSW"): _home("San Francisco", "CA", 37.7680, -122.3877),
    (LEAGUE_NBA, "HOU"): _home("Houston", "TX", 29.7508, -95.3621),
    (LEAGUE_NBA, "IND"): _home("Indianapolis", "IN", 39.7640, -86.1555),
    (LEAGUE_NBA, "LAC"): _home("Los Angeles", "CA", 34.0430, -118.2673),
    (LEAGUE_NBA, "LAL"): _home("Los Angeles", "CA", 34.0430, -118.2673),
    (LEAGUE_NBA, "MEM"): _home("Memphis", "TN", 35.1382, -90.0506),
    (LEAGUE_NBA, "MIA"): _home("Miami", "FL", 25.7814, -80.1870),
    (LEAGUE_NBA, "MIL"): _home("Milwaukee", "WI", 43.0451, -87.9172),
    (LEAGUE_NBA, "MIN"): _home("Minneapolis", "MN", 44.9795, -93.2762),
    (LEAGUE_NBA, "NO"): _home("New Orleans", "LA", 29.9490, -90.0821),
    (LEAGUE_NBA, "NOP"): _home("New Orleans", "LA", 29.9490, -90.0821),
    (LEAGUE_NBA, "NY"): _home("New York", "NY", 40.7505, -73.9934),
    (LEAGUE_NBA, "NYK"): _home("New York", "NY", 40.7505, -73.9934),
    (LEAGUE_NBA, "OKC"): _home("Oklahoma City", "OK", 35.4634, -97.5151),
    (LEAGUE_NBA, "ORL"): _home("Orlando", "FL", 28.5392, -81.3839),
    (LEAGUE_NBA, "PHI"): _home("Philadelphia", "PA", 39.9012, -75.1720),
    (LEAGUE_NBA, "PHX"): _home("Phoenix", "AZ", 33.4457, -112.0712),
    (LEAGUE_NBA, "POR"): _home("Portland", "OR", 45.5316, -122.6668),
    (LEAGUE_NBA, "SAC"): _home("Sacramento", "CA", 38.5802, -121.4997),
    (LEAGUE_NBA, "SA"): _home("San Antonio", "TX", 29.4270, -98.4375),
    (LEAGUE_NBA, "SAS"): _home("San Antonio", "TX", 29.4270, -98.4375),
    (LEAGUE_NBA, "TOR"): _home("Toronto", "ON", 43.6435, -79.3791),
    (LEAGUE_NBA, "UTA"): _home("Salt Lake City", "UT", 40.7683, -111.9011),
    (LEAGUE_NBA, "WAS"): _home("Washington", "DC", 38.8981, -77.0209),
    (LEAGUE_NBA, "WSH"): _home("Washington", "DC", 38.8981, -77.0209),
    (LEAGUE_MLB, "ARI"): _home("Phoenix", "AZ", 33.4455, -112.0667),
    (LEAGUE_MLB, "ATL"): _home("Cumberland", "GA", 33.8907, -84.4677),
    (LEAGUE_MLB, "BAL"): _home("Baltimore", "MD", 39.2839, -76.6216),
    (LEAGUE_MLB, "BOS"): _home("Boston", "MA", 42.3467, -71.0972),
    (LEAGUE_MLB, "CHC"): _home("Chicago", "IL", 41.9484, -87.6553),
    (LEAGUE_MLB, "CHW"): _home("Chicago", "IL", 41.8299, -87.6338),
    (LEAGUE_MLB, "CWS"): _home("Chicago", "IL", 41.8299, -87.6338),
    (LEAGUE_MLB, "CIN"): _home("Cincinnati", "OH", 39.0974, -84.5080),
    (LEAGUE_MLB, "CLE"): _home("Cleveland", "OH", 41.4962, -81.6852),
    (LEAGUE_MLB, "COL"): _home("Denver", "CO", 39.7559, -104.9942),
    (LEAGUE_MLB, "DET"): _home("Detroit", "MI", 42.3390, -83.0485),
    (LEAGUE_MLB, "HOU"): _home("Houston", "TX", 29.7573, -95.3555),
    (LEAGUE_MLB, "KC"): _home("Kansas City", "MO", 39.0517, -94.4803),
    (LEAGUE_MLB, "LAA"): _home("Anaheim", "CA", 33.8003, -117.8827),
    (LEAGUE_MLB, "LAD"): _home("Los Angeles", "CA", 34.0739, -118.2400),
    (LEAGUE_MLB, "MIA"): _home("Miami", "FL", 25.7781, -80.2196),
    (LEAGUE_MLB, "MIL"): _home("Milwaukee", "WI", 43.0280, -87.9712),
    (LEAGUE_MLB, "MIN"): _home("Minneapolis", "MN", 44.9817, -93.2776),
    (LEAGUE_MLB, "NYM"): _home("Flushing", "NY", 40.7571, -73.8458),
    (LEAGUE_MLB, "NYY"): _home("Bronx", "NY", 40.8296, -73.9262),
    (LEAGUE_MLB, "OAK"): _home("Sacramento", "CA", 38.5802, -121.4997),
    (LEAGUE_MLB, "ATH"): _home("Sacramento", "CA", 38.5802, -121.4997),
    (LEAGUE_MLB, "PHI"): _home("Philadelphia", "PA", 39.9061, -75.1665),
    (LEAGUE_MLB, "PIT"): _home("Pittsburgh", "PA", 40.4469, -80.0057),
    (LEAGUE_MLB, "SD"): _home("San Diego", "CA", 32.7073, -117.1566),
    (LEAGUE_MLB, "SF"): _home("San Francisco", "CA", 37.7786, -122.3893),
    (LEAGUE_MLB, "SEA"): _home("Seattle", "WA", 47.5914, -122.3326),
    (LEAGUE_MLB, "STL"): _home("St. Louis", "MO", 38.6226, -90.1928),
    (LEAGUE_MLB, "TB"): _home("St. Petersburg", "FL", 27.7683, -82.6534),
    (LEAGUE_MLB, "TEX"): _home("Arlington", "TX", 32.7511, -97.0832),
    (LEAGUE_MLB, "TOR"): _home("Toronto", "ON", 43.6414, -79.3894),
    (LEAGUE_MLB, "WSH"): _home("Washington", "DC", 38.8730, -77.0074),
    (LEAGUE_MLB, "WAS"): _home("Washington", "DC", 38.8730, -77.0074),
    (LEAGUE_NHL, "ANA"): _home("Anaheim", "CA", 33.8078, -117.8769),
    (LEAGUE_NHL, "BOS"): _home("Boston", "MA", 42.3663, -71.0622),
    (LEAGUE_NHL, "BUF"): _home("Buffalo", "NY", 42.8750, -78.8764),
    (LEAGUE_NHL, "CGY"): _home("Calgary", "AB", 51.0375, -114.0519),
    (LEAGUE_NHL, "CAR"): _home("Raleigh", "NC", 35.8033, -78.7219),
    (LEAGUE_NHL, "CHI"): _home("Chicago", "IL", 41.8807, -87.6742),
    (LEAGUE_NHL, "COL"): _home("Denver", "CO", 39.7487, -105.0077),
    (LEAGUE_NHL, "CBJ"): _home("Columbus", "OH", 39.9690, -83.0064),
    (LEAGUE_NHL, "DAL"): _home("Dallas", "TX", 32.7905, -96.8103),
    (LEAGUE_NHL, "DET"): _home("Detroit", "MI", 42.3411, -83.0552),
    (LEAGUE_NHL, "EDM"): _home("Edmonton", "AB", 53.5469, -113.4979),
    (LEAGUE_NHL, "FLA"): _home("Sunrise", "FL", 26.1584, -80.3256),
    (LEAGUE_NHL, "LA"): _home("Los Angeles", "CA", 34.0430, -118.2673),
    (LEAGUE_NHL, "LAK"): _home("Los Angeles", "CA", 34.0430, -118.2673),
    (LEAGUE_NHL, "MIN"): _home("Saint Paul", "MN", 44.9448, -93.1011),
    (LEAGUE_NHL, "MTL"): _home("Montreal", "QC", 45.4961, -73.5693),
    (LEAGUE_NHL, "NSH"): _home("Nashville", "TN", 36.1592, -86.7785),
    (LEAGUE_NHL, "NJD"): _home("Newark", "NJ", 40.7336, -74.1711),
    (LEAGUE_NHL, "NJ"): _home("Newark", "NJ", 40.7336, -74.1711),
    (LEAGUE_NHL, "NYI"): _home("Elmont", "NY", 40.7227, -73.7264),
    (LEAGUE_NHL, "NYR"): _home("New York", "NY", 40.7505, -73.9934),
    (LEAGUE_NHL, "OTT"): _home("Ottawa", "ON", 45.2969, -75.9271),
    (LEAGUE_NHL, "PHI"): _home("Philadelphia", "PA", 39.9012, -75.1720),
    (LEAGUE_NHL, "PIT"): _home("Pittsburgh", "PA", 40.4396, -79.9893),
    (LEAGUE_NHL, "SJ"): _home("San Jose", "CA", 37.3327, -121.9013),
    (LEAGUE_NHL, "SJS"): _home("San Jose", "CA", 37.3327, -121.9013),
    (LEAGUE_NHL, "SEA"): _home("Seattle", "WA", 47.6221, -122.3540),
    (LEAGUE_NHL, "STL"): _home("St. Louis", "MO", 38.6268, -90.2026),
    (LEAGUE_NHL, "TB"): _home("Tampa", "FL", 27.9427, -82.4518),
    (LEAGUE_NHL, "TBL"): _home("Tampa", "FL", 27.9427, -82.4518),
    (LEAGUE_NHL, "TOR"): _home("Toronto", "ON", 43.6435, -79.3791),
    (LEAGUE_NHL, "UTA"): _home("Salt Lake City", "UT", 40.7683, -111.9011),
    (LEAGUE_NHL, "VAN"): _home("Vancouver", "BC", 49.2778, -123.1088),
    (LEAGUE_NHL, "VGK"): _home("Las Vegas", "NV", 36.1029, -115.1784),
    (LEAGUE_NHL, "WSH"): _home("Washington", "DC", 38.8981, -77.0209),
    (LEAGUE_NHL, "WAS"): _home("Washington", "DC", 38.8981, -77.0209),
    (LEAGUE_NHL, "WPG"): _home("Winnipeg", "MB", 49.8927, -97.1436),
}


def team_home(
    league: str,
    abbreviation: str,
    espn_location: str = "",
) -> TeamHome | None:
    """Return the club's home city, if we know it."""
    key = (str(league or "").strip().lower(), str(abbreviation or "").strip().upper())
    home = TEAM_HOMES.get(key)
    if home is not None:
        return home
    city = (espn_location or "").strip()
    if not city:
        return None
    return TeamHome(city=city, region="", latitude=0.0, longitude=0.0)
