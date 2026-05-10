"""Constants for the SHMU integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "shmu"
ATTRIBUTION = "Data © SHMÚ, CC-BY 4.0"

BASE_URL = "https://opendata.shmu.sk"
OBSERVATIONS_PATH = "/meteorology/climate/now/data"
ALERTS_PATH = "/meteorology/weather/alerts/cap"

OBSERVATIONS_INTERVAL = timedelta(minutes=5)
ALERTS_INTERVAL = timedelta(minutes=5)
HTTP_TIMEOUT = 30

CONF_STATION = "station"
CONF_ALERT_REGION = "alert_region"

# CAP awareness_type code -> stable entity key.
ALERT_TYPES: dict[int, str] = {
    1: "wind",
    2: "snow_ice",
    3: "thunderstorm",
    4: "fog",
    5: "extreme_high_temperature",
    6: "extreme_low_temperature",
    7: "coastal_event",
    8: "forest_fire",
    9: "avalanche",
    10: "rain",
    11: "unknown",
    12: "flood",
    13: "rain_flood",
}

# CAP severity -> HA-friendly value.
ALERT_SEVERITY = {
    "Minor": "minor",
    "Moderate": "moderate",
    "Severe": "severe",
    "Extreme": "extreme",
    "Unknown": "unknown",
}
