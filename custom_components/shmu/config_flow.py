"""Config flow for the SHMU integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from . import stations
from .const import CONF_STATION, DOMAIN


class ShmuConfigFlow(ConfigFlow, domain=DOMAIN):
    """User-facing config flow.

    Single-step: pick the station closest to HA's configured home location,
    let the user confirm or override via dropdown.
    """

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # Only one entry — SHMU exposes the same dataset for everyone.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        nearest, distance_km = stations.nearest(
            self.hass.config.latitude,
            self.hass.config.longitude,
        )

        if user_input is not None:
            station = stations.by_id(int(user_input[CONF_STATION]))
            assert station is not None
            return self.async_create_entry(
                title=f"SHMÚ – {station.name}",
                data={CONF_STATION: station.ind_kli},
            )

        options = [
            SelectOptionDict(value=str(s.ind_kli), label=s.name)
            for s in sorted(stations.all_stations(), key=lambda s: s.name)
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_STATION, default=str(nearest.ind_kli)): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                        custom_value=False,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "nearest_name": nearest.name,
                "nearest_distance_km": f"{distance_km:.1f}",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return ShmuOptionsFlow(entry)


class ShmuOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            new_data = dict(self._entry.data) | {CONF_STATION: int(user_input[CONF_STATION])}
            self.hass.config_entries.async_update_entry(self._entry, data=new_data)
            return self.async_create_entry(title="", data={})

        current = int(self._entry.data.get(CONF_STATION, 0))
        options = [
            SelectOptionDict(value=str(s.ind_kli), label=s.name)
            for s in sorted(stations.all_stations(), key=lambda s: s.name)
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_STATION, default=str(current)): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
