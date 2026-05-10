"""Per-measurement Sensor entities for the configured SHMU station."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfIrradiance,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ShmuConfigEntry, stations
from .const import ATTRIBUTION, CONF_STATION, DOMAIN
from .coordinator import ObservationsCoordinator


@dataclass(frozen=True, kw_only=True, slots=True)
class ShmuSensorDescription(SensorEntityDescription):
    field: str
    """Key in the SHMU observation row."""


SENSORS: tuple[ShmuSensorDescription, ...] = (
    ShmuSensorDescription(
        key="temperature",
        field="t",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    ShmuSensorDescription(
        key="surface_temperature",
        field="tprz",
        translation_key="surface_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=False,
    ),
    ShmuSensorDescription(
        key="soil_temperature_5cm",
        field="t_pod5",
        translation_key="soil_temperature_5cm",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=False,
    ),
    ShmuSensorDescription(
        key="soil_temperature_10cm",
        field="t_pod10",
        translation_key="soil_temperature_10cm",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=False,
    ),
    ShmuSensorDescription(
        key="pressure",
        field="tlak",
        translation_key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.HPA,
    ),
    ShmuSensorDescription(
        key="humidity",
        field="vlh_rel",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    ShmuSensorDescription(
        key="wind_speed",
        field="vie_pr_rych",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
    ),
    ShmuSensorDescription(
        key="wind_gust",
        field="vie_max_rych",
        translation_key="wind_gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
    ),
    ShmuSensorDescription(
        key="wind_bearing",
        field="vie_pr_smer",
        translation_key="wind_bearing",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=DEGREE,
    ),
    ShmuSensorDescription(
        key="precipitation",
        field="zra_uhrn",
        translation_key="precipitation",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
    ),
    ShmuSensorDescription(
        key="snow_depth",
        field="sneh_pokr",
        translation_key="snow_depth",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
    ),
    ShmuSensorDescription(
        key="solar_radiation",
        field="zglo",
        translation_key="solar_radiation",
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
    ),
    ShmuSensorDescription(
        key="sunshine_duration",
        field="sln_trv",
        translation_key="sunshine_duration",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_registry_enabled_default=False,
    ),
    ShmuSensorDescription(
        key="visibility",
        field="dohl",
        translation_key="visibility",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
        entity_registry_enabled_default=False,
    ),
    ShmuSensorDescription(
        key="gamma_radiation",
        field="zgama",
        translation_key="gamma_radiation",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="nSv/h",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShmuConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    station = stations.by_id(int(entry.data[CONF_STATION]))
    if station is None:
        return
    async_add_entities(
        ShmuSensor(runtime.observations, station.ind_kli, station.name, desc) for desc in SENSORS
    )


class ShmuSensor(CoordinatorEntity[ObservationsCoordinator], SensorEntity):
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description: ShmuSensorDescription

    def __init__(
        self,
        coordinator: ObservationsCoordinator,
        ind_kli: int,
        station_name: str,
        description: ShmuSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._ind_kli = ind_kli
        self._attr_unique_id = f"{DOMAIN}_{ind_kli}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(ind_kli))},
            "name": f"SHMÚ – {station_name}",
            "manufacturer": "Slovenský hydrometeorologický ústav",
            "model": "Automatic weather station",
            "configuration_url": "https://www.shmu.sk",
        }

    @property
    def native_value(self) -> float | None:
        row: dict[str, Any] | None = (self.coordinator.data or {}).get(self._ind_kli)
        if not row:
            return None
        v = row.get(self.entity_description.field)
        return float(v) if isinstance(v, (int, float)) else None
