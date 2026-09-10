"""Weather labels and Open-Meteo helpers."""

from __future__ import annotations

from typing import Any

# WMO weather interpretation codes used by Open-Meteo.
WMO_ICONS: dict[int, tuple[str, str]] = {
    0: ("Clear", "sun"),
    1: ("Mostly clear", "sun"),
    2: ("Partly cloudy", "cloud_sun"),
    3: ("Cloudy", "cloud"),
    45: ("Fog", "fog"),
    48: ("Icy fog", "fog"),
    51: ("Light drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Heavy drizzle", "rain"),
    56: ("Freezing drizzle", "sleet"),
    57: ("Freezing drizzle", "sleet"),
    61: ("Light rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "sleet"),
    67: ("Freezing rain", "sleet"),
    71: ("Light snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Rain showers", "rain"),
    81: ("Rain showers", "rain"),
    82: ("Heavy showers", "rain"),
    85: ("Snow showers", "snow"),
    86: ("Heavy snow showers", "snow"),
    95: ("Thunderstorms", "storm"),
    96: ("Thunderstorms", "storm"),
    99: ("Thunderstorms", "storm"),
}


def icon_from_wmo(code: int | None) -> str:
    if code is None:
        return "unknown"
    return WMO_ICONS.get(int(code), ("Cloudy", "cloud"))[1]


def text_from_wmo(code: int | None) -> str:
    if code is None:
        return ""
    return WMO_ICONS.get(int(code), ("Cloudy", "cloud"))[0]


def icon_from_text(value: str | None) -> str:
    text = (value or "").strip().lower()
    if not text:
        return "unknown"
    if "thunder" in text or "t-storm" in text or "storm" in text:
        return "storm"
    if "snow" in text or "flurr" in text:
        return "snow"
    if "sleet" in text or "ice" in text or "freezing" in text:
        return "sleet"
    if "rain" in text or "shower" in text or "drizzle" in text:
        return "rain"
    if "fog" in text or "mist" in text or "haze" in text:
        return "fog"
    if "cloud" in text or "overcast" in text:
        return "cloud"
    if "partly" in text or "mostly sunny" in text or "mostly clear" in text:
        return "cloud_sun"
    if "sun" in text or "clear" in text or "fair" in text:
        return "sun"
    if "wind" in text:
        return "wind"
    return "cloud"


def parse_open_meteo(payload: dict[str, Any]) -> tuple[float | None, str, str]:
    """Return (temp_f, text, icon) from an Open-Meteo current-conditions payload."""
    current = payload.get("current") if isinstance(payload, dict) else None
    if not isinstance(current, dict):
        return None, "", "unknown"
    temp = current.get("temperature_2m")
    try:
        temp_f = float(temp) if temp is not None else None
    except (TypeError, ValueError):
        temp_f = None
    try:
        code = int(current.get("weather_code"))
    except (TypeError, ValueError):
        code = None
    return temp_f, text_from_wmo(code), icon_from_wmo(code)
