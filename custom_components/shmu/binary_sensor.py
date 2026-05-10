"""BinarySensor entities for active SHMU CAP weather warnings.

One entity per CAP `awareness_type` category. `is_on` is true while at least
one alert of that category is currently effective.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ShmuConfigEntry, stations
from .const import ALERT_TYPES, ATTRIBUTION, CONF_STATION, DOMAIN
from .coordinator import AlertsCoordinator


@dataclass(frozen=True, kw_only=True, slots=True)
class ShmuAlertDescription(BinarySensorEntityDescription):
    awareness_type: int


_DESCRIPTIONS: tuple[ShmuAlertDescription, ...] = tuple(
    ShmuAlertDescription(
        key=f"alert_{slug}",
        translation_key=f"alert_{slug}",
        device_class=BinarySensorDeviceClass.SAFETY,
        awareness_type=code,
    )
    for code, slug in ALERT_TYPES.items()
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
        ShmuAlertBinarySensor(runtime.alerts, station.ind_kli, station.name, desc)
        for desc in _DESCRIPTIONS
    )


class ShmuAlertBinarySensor(CoordinatorEntity[AlertsCoordinator], BinarySensorEntity):
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description: ShmuAlertDescription

    def __init__(
        self,
        coordinator: AlertsCoordinator,
        ind_kli: int,
        station_name: str,
        description: ShmuAlertDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{ind_kli}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(ind_kli))},
            "name": f"SHMÚ – {station_name}",
            "manufacturer": "Slovenský hydrometeorologický ústav",
            "model": "Automatic weather station",
            "configuration_url": "https://www.shmu.sk",
        }

    def _matching(self) -> list[dict[str, Any]]:
        rows = self.coordinator.data or []
        return [a for a in rows if a.get("awareness_type") == self.entity_description.awareness_type]

    @property
    def is_on(self) -> bool:
        return bool(self._matching())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self._matching()
        if not items:
            return {}
        # Surface the most-severe / soonest-expiring as primary.
        primary = sorted(
            items,
            key=lambda a: (
                _severity_rank(a.get("severity")),
                a.get("expires") or datetime.max,
            ),
            reverse=True,
        )[0]
        return {
            "headline": primary.get("headline"),
            "description": primary.get("description"),
            "severity": primary.get("severity"),
            "awareness_level": primary.get("awareness_level"),
            "onset": _iso(primary.get("onset")),
            "expires": _iso(primary.get("expires")),
            "geocodes": primary.get("geocodes"),
            "active_count": len(items),
        }


def _severity_rank(severity: str | None) -> int:
    return {"Minor": 1, "Moderate": 2, "Severe": 3, "Extreme": 4}.get(severity or "", 0)


def _iso(v: datetime | None) -> str | None:
    return v.isoformat() if v else None
