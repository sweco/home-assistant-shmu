"""The SHMU integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import AlertsCoordinator, ObservationsCoordinator
from .shmu_client import ShmuClient

PLATFORMS: list[Platform] = [Platform.WEATHER, Platform.SENSOR, Platform.BINARY_SENSOR]


@dataclass(slots=True)
class ShmuRuntimeData:
    """Per-config-entry runtime objects, attached to entry.runtime_data."""

    client: ShmuClient
    observations: ObservationsCoordinator
    alerts: AlertsCoordinator


type ShmuConfigEntry = ConfigEntry[ShmuRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: ShmuConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = ShmuClient(session)
    observations = ObservationsCoordinator(hass, client)
    alerts = AlertsCoordinator(hass, client)

    await observations.async_config_entry_first_refresh()
    await alerts.async_config_entry_first_refresh()

    entry.runtime_data = ShmuRuntimeData(client=client, observations=observations, alerts=alerts)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ShmuConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
