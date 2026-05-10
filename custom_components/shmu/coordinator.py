"""DataUpdateCoordinators for SHMU observations and CAP alerts."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import ALERTS_INTERVAL, DOMAIN, OBSERVATIONS_INTERVAL
from .shmu_client import ShmuApiError, ShmuClient

_LOGGER = logging.getLogger(__name__)


class ObservationsCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Polls SHMU 1-minute station observations every OBSERVATIONS_INTERVAL."""

    def __init__(self, hass: HomeAssistant, client: ShmuClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_observations",
            update_interval=OBSERVATIONS_INTERVAL,
        )
        self._client = client

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            return await self._client.fetch_latest_observation()
        except ShmuApiError as e:
            raise UpdateFailed(str(e)) from e


class AlertsCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Polls active SHMU CAP alerts every ALERTS_INTERVAL."""

    def __init__(self, hass: HomeAssistant, client: ShmuClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_alerts",
            update_interval=ALERTS_INTERVAL,
        )
        self._client = client

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            return await self._client.fetch_active_alerts()
        except ShmuApiError as e:
            raise UpdateFailed(str(e)) from e
