# BRICS Track 2 — Work Division
**Project:** AI-Powered Federated Climate Action Platform
**Track:** Track 2 — Clean Air & Climate Resilience (BRICS Theme: Sustainability)
**Deadline:** September 30, 2026
**Team:** Sujal (data pipeline + backend), Sarthak (Gemini AI), Anoushka (frontend)
**Approach:** All three using opencode agents
**Stack:** FastAPI + Streamlit → Render.com | Gemini API | OpenAQ + NASA FIRMS + WAQI + Open-Meteo

---

## WHAT WE ARE ACTUALLY BUILDING

Per the challenge statement, this is NOT just an AQI dashboard. It must:

1. **Combine** citizen-sourced data (photos, local sensors) WITH satellite imagery AND meteorological data
2. **Detect** hidden hyper-local pollution hotspots that government stations miss
3. **Forecast** future AQI spikes across BRICS economic corridors — not just show current data
4. **Alert** relevant authorities with cross-border context
5. **Be federated** — designed so BRICS nations can share predictive models

This means we have four distinct data layers:
- Layer 1: Government AQI sensors (OpenAQ, CPCB, WAQI)
- Layer 2: Satellite fire/smoke detection (NASA FIRMS)
- Layer 3: Meteorological data — wind, humidity, temperature (Open-Meteo, free, no auth)
- Layer 4: Citizen input — photos uploaded by users (Gemini Vision)

All four layers feed into Gemini which reasons across them to produce forecasts and cross-border alerts.

---

## PROJECT STRUCTURE

```
brics-air-platform/
├── backend/
│   ├── main.py                  # Sujal — FastAPI app entry point
│   ├── models.py                # Sujal — ALL Pydantic schemas (written first)
│   ├── pipeline/
│   │   ├── openaq.py            # Sujal — government AQI data
│   │   ├── firms.py             # Sujal — NASA fire hotspots
│   │   ├── waqi.py              # Sujal — backup AQI source
│   │   ├── meteo.py             # Sujal — wind + weather data
│   │   └── sensor_community.py  # Sujal — citizen sensor network
│   ├── gemini/
│   │   ├── aqi_analysis.py      # Sarthak — structured AQI interpretation
│   │   ├── photo_analysis.py    # Sarthak — citizen photo vision analysis
│   │   ├── forecast.py          # Sarthak — 24h AQI spike forecasting
│   │   ├── crossborder.py       # Sarthak — transboundary detection
│   │   └── alerts.py            # Sarthak — multilingual authority alerts
│   ├── database.py              # Sujal — SQLite storage
│   └── cache/                   # Sujal — pre-fetched demo fallback data
├── frontend/
│   └── app.py                   # Anoushka — Streamlit dashboard
├── .env                         # NEVER PUSH — share keys over WhatsApp
├── .gitignore
├── requirements.txt
└── README.md
```

---

## SUJAL — Data Pipeline & Backend

You own all four data layers and the FastAPI backbone.
Nothing else starts until your endpoints are live.

---

### Step 0 — Do This First (Day 18 Sep, today)

- Create GitHub repo `brics-air-platform`, add Sarthak and Anoushka as collaborators
- Create `.gitignore` with `.env` in it immediately before first commit
- Share `.env` template over WhatsApp (not GitHub):
```
OPENAQ_API_KEY=
FIRMS_API_KEY=
WAQI_TOKEN=
GEMINI_API_KEY=
PURPLEAIR_API_KEY=
```
- Write `requirements.txt`:
```
fastapi
uvicorn
pydantic
python-dotenv
httpx
requests
streamlit
folium
plotly
tenacity
sqlite3
```

---

### Step 1 — Write models.py FIRST (Day 19 Sep)

**This is the most important thing you do. Sarthak and Anoushka cannot start without it.**

Write these Pydantic schemas. Every module in the project uses these exact shapes.

```python
# Layer 1 — AQI sensor data
class AQIReading(BaseModel):
    city: str
    country: str
    lat: float
    lng: float
    aqi: int
    pm25: float
    pm10: float
    no2: float | None
    so2: float | None
    source: str          # "openaq" | "waqi" | "cpcb"
    timestamp: datetime

# Layer 2 — Fire/smoke from satellite
class FireHotspot(BaseModel):
    lat: float
    lng: float
    brightness: float
    frp: float           # fire radiative power
    country: str
    detected_at: datetime
    satellite: str       # "VIIRS" | "MODIS"

# Layer 3 — Meteorological
class MeteoData(BaseModel):
    lat: float
    lng: float
    city: str
    wind_speed_kmh: float
    wind_direction_deg: float   # 0-360, 0=North
    wind_direction_label: str   # "NW", "SE" etc
    temperature_c: float
    humidity_pct: float
    timestamp: datetime

# Layer 4 — Citizen input
class CitizenPhoto(BaseModel):
    city: str
    lat: float | None
    lng: float | None
    image_base64: str
    uploaded_at: datetime

# Gemini outputs — Sarthak fills these in
class GeminiAQIAnalysis(BaseModel):
    city: str
    risk_level: str
    primary_pollutant: str
    health_advisory: str
    likely_sources: list[str]
    cross_border_suspected: bool
    cross_border_contribution_pct: float
    confidence: float

class GeminiForecast(BaseModel):
    city: str
    current_aqi: int
    forecast_6h_aqi: int
    forecast_24h_aqi: int
    spike_warning: bool
    spike_cause: str
    forecast_confidence: float

class GeminiCrossBorderEvent(BaseModel):
    source_country: str
    source_city: str
    source_cause: str          # "crop burning" | "industrial" | "wildfire"
    affected_city: str
    affected_country: str
    transport_direction: str
    distance_km: float
    severity: str
    evidence_summary: str

class GeminiPhotoResult(BaseModel):
    pollution_visible: bool
    pollution_type: str
    estimated_aqi_category: str
    visibility_km: float
    severity_score: int        # 1-10
    likely_source: str
    recommendation: str
    confidence: float

class AlertMessage(BaseModel):
    city: str
    risk_level: str
    message_hindi: str
    message_portuguese: str
    message_english: str
    target_authority: str      # "Delhi Pollution Control Committee" etc
    urgency: str               # "immediate" | "advisory" | "watch"
```

Send this file to Sarthak and Anoushka the moment it's done.

---

### Step 2 — Data Pipeline (Days 19-21 Sep)

Build one module per data source. Each module must:
- Return the exact Pydantic schema defined above
- Cache response to `backend/cache/{source}.json`
- Have a fallback function with hardcoded realistic data if API is down

**openaq.py — Government AQI**
- Cities to fetch: Delhi, Mumbai, São Paulo, Beijing, Johannesburg
- Endpoint: `GET https://api.openaq.org/v3/locations?coordinates={lat},{lng}&radius=50000`
- Then: `GET https://api.openaq.org/v3/sensors/{id}/measurements?limit=1`
- Returns: list of `AQIReading`
- Opencode prompt to use:
> "Write async Python module openaq.py using httpx. Fetch latest PM2.5 and PM10 readings from OpenAQ API v3 for these cities with lat/lng: Delhi (28.6139,77.2090), Mumbai (19.0760,72.8777), São Paulo (-23.5505,-46.6333), Beijing (39.9042,116.4074), Johannesburg (-26.2041,28.0473). API key from env var OPENAQ_API_KEY in X-API-Key header. Return list of AQIReading Pydantic objects [paste schema]. Cache to backend/cache/openaq.json. Include fallback() function returning hardcoded mock data if API fails."

**firms.py — NASA Fire Hotspots**
- Regions: South Asia bbox, South America bbox
- Endpoint: `GET https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{bbox}/{days}`
- Returns: list of `FireHotspot`
- Opencode prompt:
> "Write Python module firms.py using requests. Fetch VIIRS fire hotspot data from NASA FIRMS API for two bounding boxes: South Asia (60,5,100,40) and South America (-80,-40,-30,10). API key from env var FIRMS_API_KEY. Parse CSV response. Return list of FireHotspot Pydantic objects [paste schema]. Cache to backend/cache/firms.json. Include fallback() with mock hotspot data."

**meteo.py — Wind + Weather (Open-Meteo, free, NO API KEY NEEDED)**
- Endpoint: `GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&hourly=windspeed_10m,winddirection_10m,temperature_2m,relativehumidity_2m&forecast_days=1`
- Fetch for all 5 cities
- Returns: list of `MeteoData`
- This is critical for cross-border detection — wind direction tells Gemini where pollution is going
- Opencode prompt:
> "Write async Python module meteo.py using httpx. Fetch current wind speed, wind direction, temperature, and humidity from Open-Meteo free API (no auth needed) for these cities [paste cities with lat/lng]. Convert wind direction degrees to cardinal label (N/NE/E/SE/S/SW/W/NW). Return list of MeteoData Pydantic objects [paste schema]. Cache to backend/cache/meteo.json. Include fallback() with realistic mock weather data for each city."

**sensor_community.py — Citizen Sensors (no auth needed)**
- Endpoint: `GET https://data.sensor.community/airrohr/v1/filter/country=IN` for India
- Also fetch for BR (Brazil), CN (China), ZA (South Africa)
- Returns: list of `AQIReading` with source="sensor_community"
- This is the "hyper-local" layer the challenge asks for — fills gaps between government stations
- Opencode prompt:
> "Write Python module sensor_community.py using requests. Fetch citizen PM2.5 sensor data from Sensor.Community API (no auth, include contact email as User-Agent header). Fetch for country codes: IN, BR, ZA. Filter to sensors with readings in last 2 hours. Return list of AQIReading Pydantic objects [paste schema] with source='sensor_community'. Limit to 50 readings per country. Cache to backend/cache/sensors.json. Include fallback() with mock citizen sensor data."

**waqi.py — Backup AQI**
- Only used if OpenAQ is down
- Endpoint: `GET https://api.waqi.info/feed/{city}/?token={token}`
- Returns: `AQIReading`

---

### Step 3 — FastAPI Endpoints (Day 21-22 Sep)

Build `main.py` with these endpoints. All return Pydantic models as JSON.

| Endpoint | Returns | Used By |
|----------|---------|---------|
| `GET /health` | `{"status":"ok"}` | UptimeRobot ping |
| `GET /api/aqi` | list of `AQIReading` all cities | Anoushka — dashboard |
| `GET /api/aqi?city=Delhi` | single `AQIReading` | Anoushka — city selector |
| `GET /api/fires` | list of `FireHotspot` | Anoushka — map markers |
| `GET /api/meteo?city=Delhi` | `MeteoData` | Sarthak — feeds into Gemini |
| `GET /api/sensors?country=IN` | list of `AQIReading` citizen sensors | Anoushka — hyper-local layer |
| `GET /api/analysis?city=Delhi` | `GeminiAQIAnalysis` | Anoushka — analysis panel |
| `GET /api/forecast?city=Delhi` | `GeminiForecast` | Anoushka — forecast panel |
| `GET /api/crossborder` | list of `GeminiCrossBorderEvent` | Anoushka — alert panel |
| `GET /api/alerts?city=Delhi` | `AlertMessage` | Anoushka — multilingual panel |
| `POST /api/analyze-photo` | `GeminiPhotoResult` | Anoushka — photo upload |

**Opencode prompt for main.py:**
> "Write FastAPI app main.py. Import all pipeline modules (openaq, firms, meteo, waqi, sensor_community) and all gemini modules (aqi_analysis, forecast, crossborder, alerts, photo_analysis). Build these endpoints [paste endpoint table]. Each endpoint calls the relevant pipeline module, passes data to the relevant Gemini module, returns Pydantic model as JSON response. Add CORS middleware allowing all origins. Add exception handler that returns mock data if any module fails. API runs on port 8000."

---

### Step 4 — Mock Data Fallbacks (Day 22 Sep)

For every pipeline module, pre-fetch real data once and save to `backend/cache/`. During demo, if any API is slow or down, serve from cache. Add this logic to every endpoint in main.py.

---

## SARTHAK — Gemini AI Integration

You own all AI reasoning. You receive data from Sujal's endpoints, you return structured intelligence.
Do NOT call external APIs directly. Do NOT touch frontend.

**Read first:** `backend/models.py` the moment Sujal shares it. Your entire job is producing those output schemas.

---

### Module 1 — AQI Analysis (Day 21 Sep)
**File:** `backend/gemini/aqi_analysis.py`

Input: `AQIReading` + `MeteoData` for same city
Output: `GeminiAQIAnalysis`

This is your core module. Gemini takes raw sensor numbers plus wind data and reasons about:
- What is causing this AQI level
- How much is coming from cross-border sources
- What health risk it represents

```python
# Prompt structure to use
prompt = f"""
You are an air quality expert analyzing BRICS city data.

City: {reading.city}, {reading.country}
Current AQI: {reading.aqi}
PM2.5: {reading.pm25} µg/m³ (WHO limit: 15 µg/m³/24h)
PM10: {reading.pm10} µg/m³
Wind: {meteo.wind_speed_kmh} km/h from {meteo.wind_direction_label}
Temperature: {meteo.temperature_c}°C, Humidity: {meteo.humidity_pct}%

Known context: 85% of Indian urban PM2.5 is transboundary. 
Amazon fires transport smoke 2000+ km to São Paulo.

Analyze the likely sources and cross-border contribution.
Return structured JSON only.
"""
```

Use `response_mime_type="application/json"` and `response_schema=GeminiAQIAnalysis.model_json_schema()`.
Use `gemini-2.5-flash` model.
Add tenacity retry — 3 attempts, exponential backoff.

**Opencode prompt:**
> "Write Python module aqi_analysis.py using google-genai SDK. Function analyze_aqi(reading: AQIReading, meteo: MeteoData) -> GeminiAQIAnalysis. Use Gemini 2.5 Flash with response_mime_type='application/json' and response_schema. Include this domain context in system prompt: 85% of Indian urban PM2.5 is transboundary, Amazon fires transport smoke 2000km to São Paulo. Add tenacity retry decorator 3 attempts exponential backoff. API key from GEMINI_API_KEY env var. [paste both schemas]"

---

### Module 2 — Forecast (Day 22 Sep)
**File:** `backend/gemini/forecast.py`

Input: `AQIReading` (current) + `MeteoData` + list of `FireHotspot` nearby
Output: `GeminiForecast`

This is the forecasting requirement from the challenge statement. Gemini reasons:
- Current AQI + wind direction + nearby fire hotspots = predicted AQI in 6h and 24h
- Is a spike coming? What will cause it?

```python
# Key context to include in prompt
nearby_fires = [f for f in hotspots if distance(f.lat,f.lng,reading.lat,reading.lng) < 500]
prompt = f"""
Current AQI in {reading.city}: {reading.aqi}
Wind: {meteo.wind_speed_kmh} km/h from {meteo.wind_direction_label}
Active fires within 500km: {len(nearby_fires)} hotspots
Nearest fire: {min_distance}km {upwind_or_downwind} 
Fire radiative power: {max_frp} MW

Forecast AQI for 6 hours and 24 hours from now.
Consider: wind transport time, fire intensity, typical diurnal patterns.
"""
```

**Opencode prompt:**
> "Write Python module forecast.py using google-genai SDK. Function forecast_aqi(reading: AQIReading, meteo: MeteoData, nearby_hotspots: list[FireHotspot]) -> GeminiForecast. Calculate distance between city coordinates and each fire hotspot. Determine if fires are upwind based on wind direction. Pass this context to Gemini 2.5 Flash with structured JSON output. Add tenacity retry. [paste all three schemas]"

---

### Module 3 — Cross-Border Detection (Day 23 Sep)
**File:** `backend/gemini/crossborder.py`

Input: list of `AQIReading` for multiple cities + list of `FireHotspot` + list of `MeteoData`
Output: list of `GeminiCrossBorderEvent`

This is the most impressive module. Gemini looks at wind patterns, fire locations, and AQI readings across multiple cities simultaneously and detects transboundary events.

Key scenario to demonstrate:
- Fire hotspots in Punjab, India
- Wind blowing northwest
- AQI spike in Lahore, Pakistan
- Gemini concludes: transboundary event, crop burning source, India → Pakistan direction

**Opencode prompt:**
> "Write Python module crossborder.py using google-genai SDK. Function detect_crossborder(readings: list[AQIReading], hotspots: list[FireHotspot], meteo: list[MeteoData]) -> list[GeminiCrossBorderEvent]. Build a prompt that describes all city AQI readings, all fire hotspot locations, and all wind vectors simultaneously. Ask Gemini to identify any active transboundary pollution transport events. Include known BRICS corridors in system prompt: Indo-Gangetic Plain (India-Pakistan), Amazon corridor (Brazil), Mpumalanga-Johannesburg (South Africa). Use Gemini 2.5 Pro for this one — more complex reasoning. Structured JSON output. [paste schemas]"

---

### Module 4 — Multilingual Alerts (Day 23 Sep)
**File:** `backend/gemini/alerts.py`

Input: `GeminiAQIAnalysis` + optional `GeminiCrossBorderEvent`
Output: `AlertMessage`

One Gemini call, three languages simultaneously. Include which authority to alert.

```python
prompt = f"""
Generate an official air quality alert for {analysis.city}.

Current situation: {analysis.risk_level} — {analysis.primary_pollutant}
Health advisory: {analysis.health_advisory}
Cross-border source: {crossborder.source_cause if crossborder else 'Local sources'}

Generate the alert message in THREE languages simultaneously:
1. Hindi (for Indian authorities and citizens)
2. Portuguese (for Brazilian authorities and citizens)  
3. English (for international coordination)

Also specify which authority should receive this alert immediately.
Return as structured JSON only.
"""
```

**Opencode prompt:**
> "Write Python module alerts.py using google-genai SDK. Function generate_alert(analysis: GeminiAQIAnalysis, crossborder: GeminiCrossBorderEvent | None) -> AlertMessage. Generate alert messages in Hindi, Portuguese, English in a single Gemini call. Include authority mapping: Delhi→'Delhi Pollution Control Committee', São Paulo→'CETESB São Paulo', Beijing→'Beijing Municipal Ecology Bureau'. Structured JSON output. Tenacity retry. [paste schemas]"

---

### Module 5 — Photo Analysis (Day 24 Sep)
**File:** `backend/gemini/photo_analysis.py`

Input: `CitizenPhoto` (contains base64 image)
Output: `GeminiPhotoResult`

Citizen uploads photo of smog/haze/smoke. Gemini Vision analyzes it.

**Opencode prompt:**
> "Write Python module photo_analysis.py using google-genai SDK. Function analyze_photo(photo: CitizenPhoto) -> GeminiPhotoResult. Decode base64 image, pass to Gemini Vision (gemini-2.5-flash multimodal). Prompt asks Gemini to identify pollution type, estimate visibility, rate severity 1-10, identify likely source (industrial/agricultural/wildfire/traffic), give health recommendation. Structured JSON output. Tenacity retry. [paste schemas]"

---

## ANOUSHKA — Streamlit Frontend

You own everything judges see. The dashboard IS the demo.

**Wait for:** Sujal to tell you `GET /api/aqi` and `GET /api/fires` are live before building beyond layout.
**Never call:** External APIs directly. Only call Sujal's FastAPI endpoints.

---

### What to Build

**app.py structure:**
```
Page Title: "BRICS Climate Intelligence Platform"
Sidebar:
  - City selector dropdown
  - "Upload Pollution Photo" button
  - Data source indicators (live/cached)

Main area — 3 rows:

Row 1 (top):
  - Left: AQI score big number with color
  - Middle: Risk level badge
  - Right: 24h forecast arrow (up/down/stable)

Row 2 (middle):
  - Left (60%): Folium map — fire hotspots + AQI city markers + wind arrows
  - Right (40%): Cross-border alert box

Row 3 (bottom):
  - Left: BRICS comparison bar chart (all 5 cities PM2.5)
  - Right: Multilingual alert panel (3 columns: Hindi | Portuguese | English)

Below fold:
  - Citizen photo upload + Gemini analysis result
  - Hyper-local sensor map (Sensor.Community data as small dots)
```

---

### Specific Widgets to Build

**1. City Selector**
```python
city = st.sidebar.selectbox(
    "Select City",
    ["Delhi", "Mumbai", "São Paulo", "Beijing", "Johannesburg"]
)
```
On change → re-fetch all data for selected city.

**2. AQI Color Coding**
```python
def aqi_color(aqi):
    if aqi <= 50: return "🟢"
    elif aqi <= 100: return "🟡"
    elif aqi <= 200: return "🟠"
    elif aqi <= 300: return "🔴"
    else: return "⚫"
```

**3. Folium Map**
- Center on selected city
- Red flame markers for fire hotspots
- Colored circle for each BRICS city (color = AQI level)
- Wind direction arrow on selected city (use MeteoData)
- Small grey dots for citizen sensor readings (hyper-local layer)
- Embed with `st_folium` or `st.components.v1.html`

**4. Cross-Border Alert Box**
```python
if crossborder_events:
    st.error(f"⚠️ Transboundary Event Detected")
    st.write(f"Source: {event.source_cause} in {event.source_country}")
    st.write(f"Affecting: {event.affected_city}")
    st.write(f"Direction: {event.transport_direction}")
else:
    st.success("No active cross-border events")
```

**5. BRICS Comparison Chart**
- `plotly` bar chart
- X axis: 5 cities
- Y axis: PM2.5 µg/m³
- Color each bar by AQI category
- Add WHO 24h limit line at 15 µg/m³ as red horizontal reference
- Label: "Real-time PM2.5 vs WHO Guideline (15 µg/m³)"

**6. Multilingual Alert Panel**
```python
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("🇮🇳 Hindi")
    st.write(alert.message_hindi)
with col2:
    st.subheader("🇧🇷 Portuguese")
    st.write(alert.message_portuguese)
with col3:
    st.subheader("🌐 English")
    st.write(alert.message_english)
```

**7. Forecast Panel**
```python
delta = forecast.forecast_24h_aqi - forecast.current_aqi
st.metric("24h Forecast", forecast.forecast_24h_aqi, delta=delta)
if forecast.spike_warning:
    st.warning(f"⚠️ Spike predicted: {forecast.spike_cause}")
```

**8. Photo Upload**
```python
uploaded = st.file_uploader("Upload pollution photo", type=["jpg","png","jpeg"])
if uploaded:
    # POST to /api/analyze-photo
    result = requests.post(f"{BASE_URL}/api/analyze-photo", files={"file": uploaded})
    data = GeminiPhotoResult(**result.json())
    st.write(f"Pollution type: {data.pollution_type}")
    st.write(f"Severity: {data.severity_score}/10")
    st.write(f"Recommendation: {data.recommendation}")
```

**Opencode prompt:**
> "Write Streamlit app frontend/app.py. Backend BASE_URL from env var BACKEND_URL. Build dashboard with: sidebar city dropdown, AQI metric with color coding function, folium map with fire hotspot markers and wind direction arrow and citizen sensor dots, plotly bar chart comparing PM2.5 across 5 BRICS cities with WHO reference line at 15, cross-border alert box showing red warning if event detected, three-column multilingual alert panel Hindi/Portuguese/English, st.metric forecast widget with delta, file uploader posting to /api/analyze-photo. Handle requests exceptions gracefully showing cached or mock data. [paste relevant output schemas so it knows JSON structure to parse]"

---

## INTEGRATION CHECKPOINTS

| Date | Who | What must be done |
|------|-----|------------------|
| 18 Sep | Sujal | Repo created, .env shared, requirements.txt written |
| 19 Sep | Sujal | models.py complete, shared with team |
| 20 Sep | Sujal | openaq.py + waqi.py working |
| 20 Sep | Sarthak | Read models.py, set up gemini SDK, test first call |
| 21 Sep | Sujal | firms.py + meteo.py + sensor_community.py working |
| 21 Sep | Sarthak | aqi_analysis.py working with real data from Sujal |
| 21 Sep | Anoushka | Basic layout + city selector + AQI display working |
| 22 Sep | Sujal | All FastAPI endpoints live and tested |
| 22 Sep | Sarthak | forecast.py working |
| 22 Sep | Anoushka | Folium map with fire markers working |
| 23 Sep | Sarthak | crossborder.py + alerts.py working |
| 23 Sep | Anoushka | BRICS comparison chart + multilingual panel working |
| 24 Sep | Sarthak | photo_analysis.py working |
| 24 Sep | Anoushka | Photo upload + forecast panel working |
| 25 Sep | Everyone | Full integration test — all modules connected end to end |
| 26 Sep | Sujal | Deploy to Render.com, set up UptimeRobot |
| 27 Sep | Everyone | Full demo run, find all bugs |
| 28-29 Sep | Everyone | Fix bugs only — zero new features |
| 30 Sep | Everyone | Submit |

---

## DEPLOYMENT (Sujal, Day 26 Sep)

Both backend and frontend on Render.com free tier.

**Backend:**
- Build: `pip install -r requirements.txt`
- Start: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Add all .env variables in Render → Environment tab

**Frontend:**
- Build: `pip install -r requirements.txt`
- Start: `streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0`
- Add `BACKEND_URL=https://your-render-backend-url.onrender.com` in environment

**UptimeRobot:**
- Create free account at uptimerobot.com
- Monitor: `https://your-backend.onrender.com/health` every 5 minutes
- Keeps Render from spinning down between requests

**Total cost: Free**

---

## WHAT THE DEMO LOOKS LIKE (30 Sep)

1. Open dashboard — judges see BRICS map with all 5 cities colored by current AQI
2. Select Delhi → AQI 287 in dark red, fire hotspots light up across Punjab, wind arrows show northwest flow
3. Cross-border alert: "Crop burning in Punjab, India transporting to Lahore, Pakistan — 200km northwest"
4. Forecast panel: "24h forecast: 310 (+23) — spike predicted from increased agricultural burning"
5. Multilingual panel shows same alert in Hindi, Portuguese, English simultaneously
6. Citizen sensor dots appear around Delhi — hyper-local coverage between government stations
7. Switch to São Paulo → Amazon fire hotspots, Portuguese alert auto-generated
8. Upload smog photo → Gemini: "Industrial smog, visibility 0.8km, severity 7/10, stay indoors"
9. BRICS comparison chart — all 5 cities vs WHO 15 µg/m³ line — every city is above it

That is the full demo. Four data layers, forecasting, cross-border detection, multilingual, citizen input. Every requirement from the challenge statement covered.

---

## ANTI-PATTERNS — DO NOT

- Push `.env` to GitHub
- Call external APIs from frontend directly
- Train custom ML models
- Build mobile app
- Add user authentication
- Add new features after 25 Sep
- Skip mock data fallbacks
- Use raw string Gemini outputs — always structured JSON
