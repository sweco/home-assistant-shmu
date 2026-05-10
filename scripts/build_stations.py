"""One-shot build script: extract SHMU station list (ind_kli + name) from
the public SHMU page and enrich with lat/lon via Open-Meteo geocoding.

Run once to produce custom_components/shmu/stations.json. Re-run yearly or
when SHMU publishes new stations.

    python scripts/build_stations.py

Output: prints a summary; writes ../custom_components/shmu/stations.json.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

SHMU_LIST_URL = "https://www.shmu.sk/sk/?page=1&id=meteo_apocasie_sk"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OUT_PATH = pathlib.Path(__file__).resolve().parent.parent / "custom_components" / "shmu" / "stations.json"

ROW_RE = re.compile(
    r'h_stanica" class="tl nowrap">([^<]+)</td>.*?ii=(\d+)"',
    re.DOTALL,
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "shmu-ha-build/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def extract_stations(html: str) -> list[tuple[str, int]]:
    return [(m.group(1).strip(), int(m.group(2))) for m in ROW_RE.finditer(html)]


def geocode(name: str) -> tuple[float, float, float | None] | None:
    # Stations like "Bratislava - Koliba" need the parent city as fallback.
    candidates = [name, name.split("-")[0].strip(), name.split(",")[0].strip()]
    seen: set[str] = set()
    for q in candidates:
        if q in seen:
            continue
        seen.add(q)
        params = urllib.parse.urlencode({"name": q, "count": 1, "country": "SK", "language": "sk"})
        try:
            data = json.loads(fetch(f"{GEOCODE_URL}?{params}"))
        except Exception as e:  # noqa: BLE001
            print(f"  geocode error for {q!r}: {e}", file=sys.stderr)
            continue
        results = data.get("results") or []
        if results:
            r = results[0]
            return (round(r["latitude"], 4), round(r["longitude"], 4), r.get("elevation"))
    return None


def main() -> int:
    html = fetch(SHMU_LIST_URL)
    raw = extract_stations(html)
    print(f"extracted {len(raw)} stations from SHMU page")

    out: list[dict] = []
    missing: list[tuple[str, int]] = []
    for name, ind_kli in raw:
        coords = geocode(name)
        time.sleep(0.5)  # be polite to Open-Meteo
        if coords is None:
            print(f"  [MISS] {ind_kli}  {name}")
            missing.append((name, ind_kli))
            out.append({"ind_kli": ind_kli, "name": name, "lat": None, "lon": None, "elevation": None})
            continue
        lat, lon, elev = coords
        out.append({"ind_kli": ind_kli, "name": name, "lat": lat, "lon": lon, "elevation": elev})
        print(f"  {ind_kli}  {name:35}  {lat:.4f}, {lon:.4f}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT_PATH} ({len(out)} stations, {len(missing)} unresolved)")
    if missing:
        print("Unresolved (need manual lat/lon):")
        for name, ind_kli in missing:
            print(f"  {ind_kli}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
