#!/usr/bin/env python3
"""Refresh backend/cache/*.json with the latest data.

- Sources with a key in .env  -> live fetch (saved)
- Sources without a key      -> existing committed cache is kept (never clobbered by fallback)
- No-key sources (meteo, sensors) -> always refreshed live

Usage: python scripts/refresh_cache.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from backend.pipeline import firms, meteo, openaq, sensor_community, waqi  # noqa: E402

SUMMARY: list[str] = []


def note(name: str, rows: int, source: str) -> None:
    line = f"{name:<22} {rows:>5} rows   ({source})"
    SUMMARY.append(line)
    print(f"  [{'OK' if rows else 'FAIL'}] {name:<16} {rows:>5}  {source}")


async def refresh() -> None:
    print("== BRICS Air Platform — cache refresh ==")

    # OpenAQ — needs key
    if os.getenv("OPENAQ_API_KEY"):
        try:
            rows = await openaq.fetch_aqi_all()
            note("openaq", len(rows), "live (key present)")
        except Exception as e:
            note("openaq", 0, f"live FAILED: {type(e).__name__}")
    else:
        print("  [..] openaq  skipped — OPENAQ_API_KEY missing (committed fallback cache kept)")

    # WAQI — needs token
    if os.getenv("WAQI_TOKEN"):
        try:
            rows = await waqi.fetch_all_waqi()
            note("waqi", len(rows), "live (token present)")
        except Exception as e:
            note("waqi", 0, f"live FAILED: {type(e).__name__}")
    else:
        print("  [..] waqi    skipped — WAQI_TOKEN missing (committed fallback cache kept)")

    # FIRMS — needs key
    if os.getenv("FIRMS_API_KEY"):
        try:
            rows = await asyncio.to_thread(firms.fetch_fires)
            note("firms", len(rows), "live VIIRS")
        except Exception as e:
            note("firms", 0, f"live FAILED: {type(e).__name__}")
    else:
        print("  [..] firms   skipped — FIRMS_API_KEY missing (committed cache kept)")

    # Open-Meteo — always live, no key
    try:
        rows = await meteo.fetch_meteo_all()
        note("meteo", len(rows), "live (no key)")
    except Exception as e:
        note("meteo", 0, f"FAILED: {type(e).__name__}")

    # Sensor.Community — always live, no key
    try:
        rows = await asyncio.to_thread(sensor_community.fetch_sensors)
        note("sensors", len(rows), "live (no key)")
    except Exception as e:
        note("sensors", 0, f"FAILED: {type(e).__name__}")

    print("\nCache files:")
    cache_dir = Path("backend/cache")
    for f in sorted(cache_dir.glob("*.json")):
        print(f"  {f.name:<16} {f.stat().st_size:>7} bytes")


if __name__ == "__main__":
    asyncio.run(refresh())