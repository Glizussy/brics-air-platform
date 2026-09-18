# Changelog

## Sujal — Data Pipeline + Backend

### 18 Sep 2026 — Steps 0–4 complete, all endpoints verified

**Step 0 — Repo hygiene**
- `.gitignore` — secrets (`.env`), venv, `*.db`, OS cruft. `backend/cache/*.json` intentionally TRACKED (cold-start demo fallback).
- `requirements.txt` — fixed from spec: dropped `sqlite3` (stdlib, unpipable), added `google-genai` (Sarthak), `python-multipart` (photo upload). Pinned minimums.
- `.env.example` — `OPENAQ_API_KEY / FIRMS_API_KEY / WAQI_TOKEN / GEMINI_API_KEY / BACKEND_URL`. No real `.env` committed.

**Step 1 — `backend/models.py` (contract for Sarthak + Anoushka)**
- All 9 schemas exactly as specced: `AQIReading`, `FireHotspot`, `MeteoData`, `CitizenPhoto`, `GeminiAQIAnalysis`, `GeminiForecast`, `GeminiCrossBorderEvent`, `GeminiPhotoResult`, `AlertMessage`.
- Added `BRICS_CITIES` + `CITY_LOOKUP`/`lookup_city()` single source of truth (Delhi, Mumbai, São Paulo, Beijing, Johannesburg with lat/lng). Pydantic v2, `utcnow()` default for photo timestamps.

**Step 2 — Pipeline (5 modules, each: live fetch + `save/load_cache` + `fallback()`)**
- `pipeline/openaq.py` (httpx, async) — v3 locations→latest, `X-API-Key` header, PM2.5→US-EPA-AQI conversion (`pm25_to_aqi`). No key → fallback (Delhi 287, Mumbai 132, São Paulo 68, Beijing 156, JHB 54).
- `pipeline/meteo.py` (httpx, async, no key) — Open-Meteo `current=` query, `deg_to_label()` cardinal conversion. LIVE and working (verified 18 Sep).
- `pipeline/firms.py` (requests, sync) — VIIRS_SNPP_NRT × 2 bboxes (S.Asia 60,5,100,40 + S.America −80,−40,−30,10), CSV parse, FRP-sorted cap 300. Fallback: 6 Punjab + 4 Amazon + 2 Mpumalanga hotspots.
- `pipeline/sensor_community.py` (requests, sync, no key) — `filter/country={IN,BR,CN,ZA}`, P1/P2 parse, ≤6h freshness, 50/country cap, `source="sensor_community"`. LIVE and working (41 rows fetched 18 Sep).
- `pipeline/waqi.py` (httpx, async) — backup feed per city slug, used only when OpenAQ fails; fallback mirrors OpenAQ with `source="waqi"`.

**Step 3 — `backend/main.py` (FastAPI, port 8000)**
- CORS open, `KeyError→404` handler, `GET /health`, `GET /api/cities`, `GET /api/meta`.
- Data: `GET /api/aqi[?city]`, `GET /api/fires[?limit]`, `GET /api/meteo[?city]`, `GET /api/sensors[?country]`.
- AI: `GET /api/analysis?city`, `GET /api/forecast?city`, `GET /api/crossborder`, `GET /api/alerts?city`, `POST /api/analyze-photo` (multipart `file` + `city` form field).
- Resilience: every data route is live→cache→fallback, never 500s. Gemini routes try Sarthak's `backend.gemini.*` when `GEMINI_API_KEY` is set, else deterministic rule-based fallbacks (`rule_analysis/forecast/crossborder/alert`) returning valid schemas — frontend unblocked today. Verified: `uvicorn backend.main:app` boots; TestClient 13/13 routes 200; unknown city 404; photo POST 200.

**Step 4 — Cache prefetch (`backend/cache/*.json`, committed)**
- `openaq.json` 5 rows (fallback — no key yet), `meteo.json` 5 rows (live), `firms.json` 12 rows (fallback), `sensors.json` 41 rows (live citizen sensors), `waqi.json` 5 rows (fallback mirror).

**`backend/database.py` (SQLite)**
- `brics_air.db` (gitignored), WAL mode, tables `aqi_readings/meteo/fires`; `init_db()`, `save_aqi_batch()`, `latest_aqi()`. Writes best-effort. Verified 5-row write.

**Handoff**
- Sarthak: `from backend.models import ...`; implement `backend/gemini/{aqi_analysis,forecast,crossborder,alerts,photo_analysis}.py` with functions `analyze_aqi / forecast_aqi / detect_crossborder / generate_alert / analyze_photo` — `main.py` auto-picks them up when `GEMINI_API_KEY` is set, no backend changes needed.
- Anoushka: base URL `http://localhost:8000`; start with `GET /api/aqi` + `GET /api/fires` (live now). Query params: `?city=Delhi`, `?country=IN`, `?limit=300`.

**Still pending (Sujal)**
- Real keys for OpenAQ/WAQI/Gemini over WhatsApp → re-run prefetch to replace fallback rows.
- Render deploy + UptimeRobot (Day 26 Sep per plan).

### 18 Sep 2026 — FIRMS key live
- `FIRMS_API_KEY` saved to local `.env` (gitignored, not committed).
- Verified live: South Asia bbox 505 hotspots, South America bbox 11,189 hotspots; `fetch_fires(limit=300)` returns FRP-sorted VIIRS rows.
- `backend/cache/firms.json` refreshed from 12-row fallback to 300-row live snapshot (56K). `GET /api/fires` serves live data.
- Still missing: `OPENAQ_API_KEY`, `WAQI_TOKEN`, `GEMINI_API_KEY` (OpenAQ/WAQI fallbacks active, Gemini routes on rule-based stand-ins).

### 18 Sep 2026 — README added + pushed
- `README.md`: quickstart, endpoint table, key sources, structure, team. Committed + pushed to `origin/main`.
