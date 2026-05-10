"""Async client for the SHMU open-data server.

Wraps the directory-listing-style endpoints under https://opendata.shmu.sk.
Designed to use Home Assistant's shared aiohttp ClientSession.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp
import async_timeout

from .const import ALERTS_PATH, BASE_URL, HTTP_TIMEOUT, OBSERVATIONS_PATH

_LOGGER = logging.getLogger(__name__)

_HREF_RE = re.compile(r'href="([^"?][^"]*)"')
_OBS_FILE_RE = re.compile(r"^aws1min[^\"]*\.json$")
_CAP_NS = "{urn:oasis:names:tc:emergency:cap:1.2}"


class ShmuApiError(Exception):
    """Raised when the SHMU server returns no usable data."""


class ShmuClient:
    """Thin async client over opendata.shmu.sk."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def fetch_latest_observation(self) -> dict[int, dict[str, Any]]:
        """Return the most recent 1-minute observation row per station.

        SHMU publishes one JSON file every 5 minutes containing all stations.
        Each file holds multiple minute-records per station; we keep only the
        newest minute per station to mirror "current conditions".
        """
        for d in (datetime.now(UTC).date(), datetime.now(UTC).date() - timedelta(days=1)):
            url = f"{BASE_URL}{OBSERVATIONS_PATH}/{d:%Y%m%d}/"
            try:
                files = await self._list_dir(url)
            except ShmuApiError:
                continue
            json_files = sorted(f for f in files if _OBS_FILE_RE.match(f))
            if not json_files:
                continue
            payload = await self._get_json(url + json_files[-1])
            return _select_latest_per_station(payload.get("data") or [])
        raise ShmuApiError("no observation data available for today or yesterday (UTC)")

    async def fetch_active_alerts(self) -> list[dict[str, Any]]:
        """Return all CAP alerts whose <expires> is in the future."""
        now = datetime.now(UTC)
        alerts: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        # Walk today + yesterday folders to handle UTC midnight rollover.
        for d in (now.date(), now.date() - timedelta(days=1)):
            day_url = f"{BASE_URL}{ALERTS_PATH}/{d:%Y%m%d}/"
            try:
                hhmm_dirs = await self._list_dir(day_url)
            except ShmuApiError:
                continue
            for hhmm in hhmm_dirs:
                if not hhmm.endswith("/"):
                    continue
                folder_url = day_url + hhmm
                try:
                    files = await self._list_dir(folder_url)
                except ShmuApiError:
                    continue
                for fname in files:
                    if not fname.endswith(".cap.xml"):
                        continue
                    try:
                        xml = await self._get_text(folder_url + fname)
                        parsed = _parse_cap(xml)
                    except (aiohttp.ClientError, ET.ParseError, ValueError) as e:
                        _LOGGER.debug("skipping %s: %s", fname, e)
                        continue
                    if parsed is None:
                        continue
                    if parsed["identifier"] in seen_ids:
                        continue
                    if parsed["expires"] and parsed["expires"] <= now:
                        continue
                    if parsed["status"] != "Actual":
                        continue
                    seen_ids.add(parsed["identifier"])
                    alerts.append(parsed)
        return alerts

    # ---- internals -------------------------------------------------------

    async def _list_dir(self, url: str) -> list[str]:
        html = await self._get_text(url)
        # Strip Apache sort links (start with "?" or are absolute paths).
        out: list[str] = []
        for h in _HREF_RE.findall(html):
            if h.startswith(("?", "/", "http")):
                continue
            out.append(h)
        if not out:
            raise ShmuApiError(f"empty directory listing at {url}")
        return out

    async def _get_text(self, url: str) -> str:
        async with async_timeout.timeout(HTTP_TIMEOUT):
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    raise ShmuApiError(f"HTTP {resp.status} for {url}")
                return await resp.text()

    async def _get_json(self, url: str) -> dict[str, Any]:
        async with async_timeout.timeout(HTTP_TIMEOUT):
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    raise ShmuApiError(f"HTTP {resp.status} for {url}")
                return await resp.json(content_type=None)


def _select_latest_per_station(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    latest: dict[int, dict[str, Any]] = {}
    for row in rows:
        ind = row.get("ind_kli")
        if ind is None:
            continue
        prev = latest.get(ind)
        if prev is None or (row.get("minuta") or "") > (prev.get("minuta") or ""):
            latest[ind] = row
    return latest


def _parse_cap(xml: str) -> dict[str, Any] | None:
    root = ET.fromstring(xml)
    ident = (root.findtext(f"{_CAP_NS}identifier") or "").strip()
    status = (root.findtext(f"{_CAP_NS}status") or "").strip()
    info = root.find(f"{_CAP_NS}info")
    if info is None or not ident:
        return None

    def _t(tag: str) -> str | None:
        v = info.findtext(f"{_CAP_NS}{tag}")
        return v.strip() if v else None

    awareness_type: int | None = None
    awareness_level: str | None = None
    for param in info.findall(f"{_CAP_NS}parameter"):
        name = (param.findtext(f"{_CAP_NS}valueName") or "").strip()
        value = (param.findtext(f"{_CAP_NS}value") or "").strip()
        if name == "awareness_type":
            try:
                awareness_type = int(value.split(";", 1)[0])
            except ValueError:
                pass
        elif name == "awareness_level":
            awareness_level = value

    geocodes: list[str] = []
    for area in info.findall(f"{_CAP_NS}area"):
        for gc in area.findall(f"{_CAP_NS}geocode"):
            v = gc.findtext(f"{_CAP_NS}value")
            if v:
                geocodes.append(v.strip())

    return {
        "identifier": ident,
        "status": status,
        "event": _t("event"),
        "severity": _t("severity"),
        "urgency": _t("urgency"),
        "certainty": _t("certainty"),
        "headline": _t("headline"),
        "description": _t("description"),
        "instruction": _t("instruction"),
        "onset": _parse_iso(_t("onset")),
        "effective": _parse_iso(_t("effective")),
        "expires": _parse_iso(_t("expires")),
        "awareness_type": awareness_type,
        "awareness_level": awareness_level,
        "geocodes": geocodes,
    }


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    # CAP timestamps are ISO 8601 with timezone, e.g. 2026-05-12T16:00:00-00:00.
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
