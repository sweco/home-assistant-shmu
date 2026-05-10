"""Weather entity backed by SHMU current observations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.weather import (
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    WeatherEntity,
)
from homeassistant.const import (
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ShmuConfigEntry, stations
from .const import ATTRIBUTION, CONF_STATION, DOMAIN
from .coordinator import ObservationsCoordinator

# SYNOP-style present-weather codes used by SHMU `stav_poc`.
# Mapping is intentionally coarse — SHMU's field is sparse (often null).
_PRESENT_WEATHER: dict[int, str] = {
    0: ATTR_CONDITION_SUNNY,
    1: ATTR_CONDITION_PARTLYCLOUDY,
    2: ATTR_CONDITION_PARTLYCLOUDY,
    3: ATTR_CONDITION_CLOUDY,
    **{c: ATTR_CONDITION_FOG for c in range(40, 50)},
    **{c: ATTR_CONDITION_RAINY for c in (50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65)},
    **{c: ATTR_CONDITION_POURING for c in (66, 67, 80, 81, 82)},
    **{c: ATTR_CONDITION_SNOWY for c in (70, 71, 72, 73, 74, 75, 76, 77, 78, 85, 86)},
    **{c: ATTR_CONDITION_SNOWY_RAINY for c in (68, 69, 83, 84)},
    **{c: ATTR_CONDITION_LIGHTNING_RAINY for c in range(91, 100)},
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShmuConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    station = stations.by_id(int(entry.data[CONF_STATION]))
    if station is None:
        return
    async_add_entities([ShmuWeather(runtime.observations, station.ind_kli, station.name)])


class ShmuWeather(CoordinatorEntity[ObservationsCoordinator], WeatherEntity):
    _attr_attribution = ATTRIBUTION
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: ObservationsCoordinator, ind_kli: int, station_name: str) -> None:
        super().__init__(coordinator)
        self._ind_kli = ind_kli
        self._attr_unique_id = f"{DOMAIN}_{ind_kli}_weather"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(ind_kli))},
            "name": f"SHMÚ – {station_name}",
            "manufacturer": "Slovenský hydrometeorologický ústav",
            "model": "Automatic weather station",
            "configuration_url": "https://www.shmu.sk",
        }

    @property
    def _row(self) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get(self._ind_kli)

    @property
    def available(self) -> bool:
        return super().available and self._row is not None

    @property
    def native_temperature(self) -> float | None:
        return _f(self._row, "t")

    @property
    def native_pressure(self) -> float | None:
        return _f(self._row, "tlak")

    @property
    def humidity(self) -> float | None:
        return _f(self._row, "vlh_rel")

    @property
    def native_wind_speed(self) -> float | None:
        return _f(self._row, "vie_pr_rych")

    @property
    def native_wind_gust_speed(self) -> float | None:
        return _f(self._row, "vie_max_rych")

    @property
    def wind_bearing(self) -> float | None:
        return _f(self._row, "vie_pr_smer")

    @property
    def native_visibility(self) -> float | None:
        v = _f(self._row, "dohl")
        return v / 1000.0 if v is not None else None  # m -> km

    @property
    def condition(self) -> str | None:
        row = self._row
        if not row:
            return None
        code = row.get("stav_poc")
        if code is None:
            return _condition_fallback(row)
        try:
            return _PRESENT_WEATHER.get(int(code)) or _condition_fallback(row)
        except (TypeError, ValueError):
            return _condition_fallback(row)


def _f(row: dict[str, Any] | None, key: str) -> float | None:
    if not row:
        return None
    v = row.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _condition_fallback(row: dict[str, Any]) -> str | None:
    """When SHMU's `stav_poc` is null, derive a coarse condition from numbers."""
    rain = _f(row, "zra_uhrn")
    snow = _f(row, "sneh_pokr")
    visibility = _f(row, "dohl")
    if rain and rain > 0:
        return ATTR_CONDITION_RAINY
    if snow and snow > 0 and (rain or 0) == 0:
        return ATTR_CONDITION_SNOWY
    if visibility is not None and visibility < 1000:
        return ATTR_CONDITION_FOG
    sunshine = _f(row, "sln_trv")
    if sunshine and sunshine > 30:
        return ATTR_CONDITION_SUNNY
    return ATTR_CONDITION_PARTLYCLOUDY
