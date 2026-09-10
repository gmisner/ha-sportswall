"""Great-circle distance between two points."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_KM = 6371.0088
MILES_PER_KM = 0.621371


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the distance in kilometres between two WGS84 points."""
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    chord = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * EARTH_KM * asin(min(1.0, sqrt(chord)))


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return haversine_km(lat1, lon1, lat2, lon2) * MILES_PER_KM


def has_coords(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    return not (lat == 0.0 and lon == 0.0)
