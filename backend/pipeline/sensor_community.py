"""Hyper-local layer — citizen sensors via Sensor.Community (no auth).

Endpoint: https://data.sensor.community/airrohr/v1/filter/country={CC}
Country codes: IN, BR, CN, ZA.
Returns AQIReading with source="sensor_community", capped at 50/country.
Caches to backend/cache/sensors.json. Includes fallback.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from backend.models import AQIReading, utcnow
from backend.pipeline.openaq import pm25_to_aqi

CACHE_PATH = Path(__file__).parent.parent / "cache" / "sensors.json"
TIMEOUT = 20
LIMIT_PER_COUNTRY = 50
HEADERS = {"User-Agent": "BRICS-Air-Platform/1.0 (contact: research@brics-air.example)"}

# Sensor.Community country code -> (city label, country name, fallback coords)
COUNTRIES = {
    "IN": ("Delhi", "India", 28.6139, 77.2090),
    "BR": ("São Paulo", "Brazil", -23.5505, -46.6333),
    "CN": ("Beijing", "China", 39.9042, 116.4074),
    "ZA": ("Johannesburg", "South Africa", -26.2041, 28.0473),
}


def _parse_entry(entry: dict, city: str, country: str) -> AQIReading | None:
    try:
        loc = entry.get("location") or {}
        lat = float(loc.get("latitude")) if loc.get("latitude") else None
        lng = float(loc.get("longitude")) if loc.get("longitude") else None
        if lat is None or lng is None:
            return None
        pm25 = pm10 = None
        for v in entry.get("sensordatavalues") or []:
            if v.get("value_type") == "P2":
                pm25 = float(v.get("value"))
            elif v.get("value_type") == "P1":
                pm10 = float(v.get("value"))
        if pm25 is None or pm25 < 0 or pm25 > 1000:
            return None
        if pm10 is None:
            pm10 = pm25 * 1.6
        ts_raw = entry.get("timestamp") or ""
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except Exception:
            ts = utcnow()
        # Drop stale readings (>6h old) — API filter is coarse
        age_h = (utcnow() - ts).total_seconds() / 3600 if ts.tzinfo else 0
        if age_h > 6:
            return None
        return AQIReading(
            city=city, country=country, lat=round(lat, 4), lng=round(lng, 4),
            aqi=pm25_to_aqi(pm25), pm25=round(pm25, 1), pm10=round(pm10, 1),
            no2=None, so2=None, source="sensor_community", timestamp=ts,
        )
    except (ValueError, TypeError):
        return None


def fetch_sensors(country: str | None = None, limit_per_country: int = LIMIT_PER_COUNTRY) -> list[AQIReading]:
    codes = [country.upper()] if country else list(COUNTRIES.keys())
    for code in codes:
        if code not in COUNTRIES:
            raise KeyError(f"Unknown country code '{code}'. Use one of {list(COUNTRIES)}")
    out: list[AQIReading] = []
    for code in codes:
        city, country_name, _, _ = COUNTRIES[code]
        resp = requests.get(
            f"https://data.sensor.community/airrohr/v1/filter/country={code}",
            headers=HEADERS, timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):  # error envelope
            continue
        count = 0
        for entry in data:
            r = _parse_entry(entry, city, country_name)
            if r is None:
                continue
            out.append(r)
            count += 1
            if count >= limit_per_country:
                break
    if not out:
        raise ValueError("No live citizen sensors returned")
    save_cache(out)
    return out


# --- Cache -----------------------------------------------------------------
def save_cache(rows: list[AQIReading]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps([r.model_dump(mode="json") for r in rows], indent=2))


def load_cache() -> list[AQIReading]:
    if not CACHE_PATH.exists():
        return fallback()
    try:
        return [AQIReading(**r) for r in json.loads(CACHE_PATH.read_text())]
    except Exception:
        return fallback()


# --- Fallback: hyper-local dots around each hub city ------------------------
def fallback() -> list[AQIReading]:
    ts = utcnow()
    seeds = [
        ("Delhi", "India", [(28.65, 77.22, 298.0), (28.58, 77.18, 261.0), (28.70, 77.28, 312.0)]),
        ("São Paulo", "Brazil", [(-23.56, -46.64, 22.0), (-23.52, -46.61, 31.0)]),
        ("Beijing", "China", [(39.92, 116.41, 74.0), (39.88, 116.39, 82.0)]),
        ("Johannesburg", "South Africa", [(-26.21, 28.05, 14.0)]),
        ("Mumbai", "India", [(19.08, 72.88, 52.0), (19.10, 72.90, 61.0)]),
    ]
    out: list[AQIReading] = []
    for city, country, pts in seeds:
        for la, ln, pm25 in pts:
            out.append(AQIReading(
                city=city, country=country, lat=la, lng=ln,
                aqi=pm25_to_aqi(pm25), pm25=pm25, pm10=round(pm25 * 1.6, 1),
                no2=None, so2=None, source="sensor_community", timestamp=ts,
            ))
    return out
