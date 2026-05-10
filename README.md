# SHMÚ – Home Assistant integration

Custom integration that surfaces data from the **Slovak Hydrometeorological
Institute** ([SHMÚ](https://www.shmu.sk)) open-data server inside Home
Assistant. Works on **all** Home Assistant install types (HA OS, Supervised,
Container/Docker, Core) — it ships as a custom integration, not a Supervisor
add-on.

## What you get

- **`weather.shmu_*`** – current conditions from the closest automatic weather station
- **Sensor entities** per measurement: temperature, humidity, pressure, wind speed/gust/bearing, precipitation, snow depth, solar radiation, soil temperatures, visibility, gamma radiation
- **`binary_sensor.shmu_alert_*`** – one entity per CAP `awareness_type` (wind, thunderstorm, snow/ice, frost, fog, heat, flood, rain, …); turns on while a SHMÚ warning is active, with severity / onset / expires / headline as attributes

Data is polled from <https://opendata.shmu.sk> every 5 minutes. No registration
or API key.

## Install

### HACS (recommended)

1. HACS → ⋮ → *Custom repositories* → add this repo URL, category *Integration*
2. Install **SHMÚ**
3. Restart Home Assistant
4. Settings → Devices & Services → *Add integration* → **SHMÚ**

### Manual

Copy `custom_components/shmu/` into your HA config's `custom_components/`
directory and restart.

## Configuration

The config flow auto-detects the SHMÚ station closest to your Home Assistant
location (`Settings → System → General → Location`). You can override the
station from the dropdown either during initial setup or later via
*Configure* on the integration tile.

## Roadmap

- **Phase 2** — radar `camera` entity (parses ODIM HDF5 composite from `/meteorology/weather/radar/`)
- **Phase 3** — ALADIN forecast integration (parses GRIB2 from `/meteorology/weather/nwp/aladin/`); will land in the `weather` entity's forecast attribute

Both will be opt-in to keep Phase 1 dependency-free for minimal Container installs.

## Data attribution

Data © Slovenský hydrometeorologický ústav, distributed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Each entity
carries the required attribution in its state attributes.

Dataset metadata: <https://data.slovensko.sk/datasety/9bdd8179-9cb0-46c6-a0d0-a52e50d2e2bc>
