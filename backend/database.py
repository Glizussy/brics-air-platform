"""SQLite storage — Sujal.

Tiny persistence layer so the demo can show history and survive restarts.
Tables: aqi_readings, meteo, fires. All writes are best-effort (never crash API).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "brics_air.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS aqi_readings (
    city TEXT, country TEXT, lat REAL, lng REAL, aqi INTEGER,
    pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, source TEXT, timestamp TEXT
);
CREATE TABLE IF NOT EXISTS meteo (
    city TEXT, lat REAL, lng REAL, wind_speed_kmh REAL,
    wind_direction_deg REAL, wind_direction_label TEXT,
    temperature_c REAL, humidity_pct REAL, timestamp TEXT
);
CREATE TABLE IF NOT EXISTS fires (
    lat REAL, lng REAL, brightness REAL, frp REAL,
    country TEXT, detected_at TEXT, satellite TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(_SCHEMA)
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(_SCHEMA)


def save_aqi_batch(rows: list[dict]) -> int:
    """rows: list of AQIReading.model_dump(mode='json'). Returns rows written."""
    if not rows:
        return 0
    try:
        with get_conn() as conn:
            conn.executemany(
                "INSERT INTO aqi_readings VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [(r.get("city"), r.get("country"), r.get("lat"), r.get("lng"),
                  r.get("aqi"), r.get("pm25"), r.get("pm10"), r.get("no2"),
                  r.get("so2"), r.get("source"), str(r.get("timestamp"))) for r in rows],
            )
        return len(rows)
    except Exception:
        return 0


def latest_aqi(limit: int = 50) -> list[dict]:
    try:
        with get_conn() as conn:
            cur = conn.execute("SELECT * FROM aqi_readings ORDER BY timestamp DESC LIMIT ?", (limit,))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception:
        return []
