"""SHMU station catalogue + nearest-station lookup."""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass
from functools import lru_cache

_STATIONS_FILE = pathlib.Path(__file__).with_name("stations.json")


@dataclass(frozen=True, slots=True)
class Station:
    ind_kli: int
    name: str
    lat: float
    lon: float
    elevation: float | None


@lru_cache(maxsize=1)
def all_stations() -> tuple[Station, ...]:
    raw = json.loads(_STATIONS_FILE.read_text(encoding="utf-8"))
    return tuple(
        Station(
            ind_kli=int(s["ind_kli"]),
            name=str(s["name"]),
            lat=float(s["lat"]),
            lon=float(s["lon"]),
            elevation=float(s["elevation"]) if s.get("elevation") is not None else None,
        )
        for s in raw
        if s.get("lat") is not None and s.get("lon") is not None
    )


def by_id(ind_kli: int) -> Station | None:
    for s in all_stations():
        if s.ind_kli == ind_kli:
            return s
    return None


def nearest(lat: float, lon: float) -> tuple[Station, float]:
    """Return (station, distance_km) to the closest station from the catalogue."""
    stations = all_stations()
    if not stations:
        raise RuntimeError("station catalogue is empty")
    best: Station = stations[0]
    best_dist = _haversine_km(lat, lon, best.lat, best.lon)
    for s in stations[1:]:
        d = _haversine_km(lat, lon, s.lat, s.lon)
        if d < best_dist:
            best, best_dist = s, d
    return best, best_dist


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
