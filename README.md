# SHELLOC Backend

> **S**mart **H**ydro-**E**nvironmental **L**ocator and C**l**eaner — Closed-Loop Bioremediation Backend Service

Backend API for **SHELLOC**, an autonomous water-remediation robotic vessel performing closed-loop **Moringa-Chitosan bio-flocculation**, **Citric Acid pH stabilization**, and **Biochar/Mesh particulate filtration** in freshwater lakes, rivers, reservoirs, and coastal perimeters.

---

## Project Overview

- **Ingests Real-Time Telemetry:** Accepts live heartbeat pushes (Turbidity, pH, TDS, Temperature, SONAR, NIR Floc Score, GPS coordinates) from the robot's edge hardware over cellular GPRS/4G.
- **Orchestrates a 9-Stage Closed-Loop State Machine:** Tracks the full remediation lifecycle from `idle` through `completed`, enforcing strict state transition rules at the API layer.
- **Broadcasts Real-Time State via WebSocket:** Pushes instant updates (`/ws/robot/{id}`) on every heartbeat to companion clients (web and mobile dashboards).
- **Powers Google Gemini AI Insights:** Uses `gemini-3.6-flash` (with `gemini-3.5-flash` as fallback) to provide non-technical operators with conversational diagnostics and remediation guidance.
- **Manages Mission Waypoints:** Stores, queries, and resolves before/after sensor readings per treatment point.

---

## Tech Stack

| Layer            | Technology                                      |
|------------------|-------------------------------------------------|
| Web Framework    | FastAPI (Async ASGI)                            |
| Database Driver  | Motor (Async MongoDB)                           |
| Database         | MongoDB Atlas / Local Replica                   |
| Data Validation  | Pydantic v2                                     |
| Real-Time Comms  | WebSockets (`/ws/robot/{id}`)                   |
| AI Engine        | Google Gemini (`gemini-3.6-flash` via `google-genai` SDK) |
| Environment Config | `python-dotenv`                               |
| Server           | Uvicorn with `uvloop`                           |

---

## Getting Started

### Prerequisites

- Python 3.11+
- A running MongoDB instance (port `27017`) **or** a MongoDB Atlas URI
- A Google Gemini API Key

### Local Installation

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your values (see Environment Variables section below)

# 4. Launch development server (hot-reload enabled)
uvicorn app.main:app --reload --port 8000
```

### Interactive API Documentation

Once the server is running, full auto-generated API docs are available at:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Environment Variables

All configuration is driven by environment variables. Create a `.env` file in the project root using `.env.example` as the template.

| Variable       | Required | Default              | Description                                                                      |
|----------------|----------|----------------------|----------------------------------------------------------------------------------|
| `MONGO_URI`    | ✅ Yes   | —                    | Full MongoDB connection string (e.g., `mongodb://localhost:27017` or Atlas URI). |
| `DB_NAME`      | ✅ Yes   | —                    | The MongoDB database name to use (e.g., `shelloc_db`).                           |
| `API_KEY`      | ✅ Yes   | —                    | Secret key used by the robot to authenticate its heartbeat/POST requests. Must be sent in the `X-API-Key` header. |
| `AI_PROVIDER`  | No       | —                    | AI provider identifier. Set to `gemini` to enable the AI chat feature.           |
| `AI_API_KEY`   | No       | —                    | Your Google Gemini API key (from [aistudio.google.com](https://aistudio.google.com)). |
| `AI_MODEL`     | No       | `gemini-3.6-flash`   | The Gemini model to use. Falls back to `gemini-3.5-flash` automatically on error. |
| `CORS_ORIGINS` | No       | `*`                  | Comma-separated list of allowed CORS origins for companion clients.               |

---

## Robot Integration Guide

This section is intended for the **robot firmware developer** integrating SHELLOC's physical hardware with this backend API.

### Authentication

All robot-to-server requests (POST, PATCH on protected routes) must include the following HTTP header:

```
X-API-Key: <your_API_KEY_value>
```

The server will respond with `403 Forbidden` if this header is missing or incorrect.

---

### The 9-Stage Mission State Machine

The robot firmware is the **source of truth** for `mission_state`. The backend stores and serves the state but does not drive the transitions. The robot must push the correct `mission_state` on each heartbeat.

```
idle  →  navigating  →  baseline_evaluating  →  dispensing_flocculant
→  incubating_15m  →  mesh_biochar_filtering  →  post_evaluating
→  adaptive_stabilization  →  completed  →  (idle)
```

> ⚠️ **Critical Rule:** The backend will reject any `PATCH /api/robot-status/{robot_id}` dispatch command (from the operator UI) if `mission_state` is not `idle` or `completed`. This prevents race conditions.

---

### Robot Heartbeat Loop

The robot sends a `POST` request to the status endpoint on every cycle (e.g., every 5–10 seconds). This is the primary data ingestion mechanism.

**Endpoint:** `POST /api/robot-status/{robot_id}`

**Required Header:** `X-API-Key: <API_KEY>`

**Request Body:**
```json
{
  "mission_state": "navigating",
  "current_lat": 14.60012,
  "current_lng": 120.98565,
  "battery_percent": 82,
  "gps_signal": "good",
  "turbidity_ntu": 134.2,
  "ph": 5.1,
  "dissolved_oxygen": 3.9,
  "tds_ppm": 410,
  "temperature_c": 28.5,
  "water_depth_m": 1.2,
  "buoyancy_failsafe_active": false,
  "flocculant_level_percent": 95,
  "target_waypoint_id": "64f1a2b3c4d5e6f7a8b9c0d1"
}
```

**All fields are optional** — only send what your hardware has available. The server uses `exclude_unset` and only updates the fields you provide, preserving existing values.

**Server-Computed Response Fields (do not send these):**
- `overall_status`: Automatically computed from `battery_percent` and `gps_signal`.
- `last_sync`: Server UTC timestamp of the last successful heartbeat.

**How the robot picks up its dispatch command:**
1. An operator taps "Dispatch" in the UI → the server writes `target_waypoint_id` to the robot's status document.
2. On the **next heartbeat response**, the `target_waypoint_id` field in the JSON response will be populated.
3. The robot reads `target_waypoint_id` from the response and begins navigating.
4. The robot sets `mission_state = "navigating"` on the subsequent heartbeat to signal it has acknowledged the command.

---

### Logging Sensor Readings

After arriving at a waypoint, the robot should log a **before** and **after** sensor reading. These readings are linked to the waypoint document and power the comparative telemetry cards in the dashboard.

**Endpoint:** `POST /api/sensor-readings/`

**Required Header:** `X-API-Key: <API_KEY>`

**Request Body:**
```json
{
  "robot_id": "shelloc-01",
  "waypoint_id": "64f1a2b3c4d5e6f7a8b9c0d1",
  "turbidity_ntu": 134.2,
  "ph": 5.1,
  "dissolved_oxygen": 3.9,
  "tds_ppm": 410,
  "temperature_c": 28.5,
  "nir_floc_score": 0.87,
  "reading_type": "before"
}
```

> `reading_type` should be `"before"` (taken at arrival) or `"after"` (taken after full treatment cycle).

The server automatically computes and stores a `status` field (`"good"` / `"borderline"` / `"critical"`) based on turbidity and pH thresholds.

---

### Logging a Treatment Event

When the robot begins dispensing flocculant, log a treatment event to create a timestamped record.

**Endpoint:** `POST /api/treatment-events/`

**Required Header:** `X-API-Key: <API_KEY>`

**Request Body:**
```json
{
  "robot_id": "shelloc-01",
  "waypoint_id": "64f1a2b3c4d5e6f7a8b9c0d1",
  "reagent_type": "citric_acid",
  "dosage_ml": 150
}
```

---

## Full REST API Reference

### 🔵 Robot Status — `/api/robot-status`

| Method   | Endpoint                    | Auth        | Description                                                                   |
|----------|-----------------------------|-------------|-------------------------------------------------------------------------------|
| `POST`   | `/{robot_id}`               | `X-API-Key` | **Robot Heartbeat.** Upserts the robot's full telemetry state. Broadcasts via WebSocket on every call. |
| `GET`    | `/{robot_id}`               | None        | Get the latest stored status for a robot. Returns `404` if robot has never checked in. |
| `PATCH`  | `/{robot_id}`               | None        | **Operator Dispatch.** Sets `target_waypoint_id`. Returns `400` if `mission_state` is not `idle` or `completed`. |

---

### 📍 Waypoints — `/api/waypoints`

| Method   | Endpoint              | Auth  | Description                                                                 |
|----------|-----------------------|-------|-----------------------------------------------------------------------------|
| `POST`   | `/`                   | None  | Create a new waypoint. Max **6 waypoints** per robot enforced.              |
| `GET`    | `/`                   | None  | List all waypoints. Optional `?robot_id=` and `?limit=` query params.       |
| `GET`    | `/robot/{robot_id}`   | None  | List all waypoints for a specific robot (preferred route for dashboards).   |
| `GET`    | `/{id}`               | None  | Get a single waypoint with **resolved** `before_reading` and `after_reading` objects embedded in the response. |
| `PATCH`  | `/{id}`               | None  | Update waypoint fields (e.g., `treated: true`, `treated_at`, reading IDs). |
| `DELETE` | `/{id}`               | None  | Delete a waypoint by ID.                                                    |

---

### 📊 Sensor Readings — `/api/sensor-readings`

| Method | Endpoint       | Auth        | Description                                                               |
|--------|----------------|-------------|---------------------------------------------------------------------------|
| `POST` | `/`            | `X-API-Key` | Log a new sensor reading linked to a waypoint.                            |
| `GET`  | `/latest`      | None        | Get the single most recent reading **per waypoint** for a given `?robot_id=`. Used by the dashboard. |
| `GET`  | `/`            | None        | List readings. Optional `?robot_id=`, `?waypoint_id=`, `?limit=` filters. |
| `GET`  | `/{id}`        | None        | Get a single sensor reading by ID.                                        |

---

### 🧪 Treatment Events — `/api/treatment-events`

| Method | Endpoint | Auth        | Description                                                     |
|--------|----------|-------------|-----------------------------------------------------------------|
| `POST` | `/`      | `X-API-Key` | Log a new treatment event (timestamps `started_at` automatically). |
| `GET`  | `/`      | None        | List events. Optional `?robot_id=`, `?waypoint_id=`, `?limit=`. |
| `GET`  | `/{id}`  | None        | Get a single treatment event by ID.                             |

---

### 🤖 AI Chat — `/api/ai-chat`

| Method | Endpoint    | Auth | Description                                                                                         |
|--------|-------------|------|-----------------------------------------------------------------------------------------------------|
| `POST` | `/`         | None | Send a user message. The server fetches live telemetry context, calls Gemini, and returns the AI reply. Persists both sides of the conversation. |
| `GET`  | `/history`  | None | Retrieve chat history for a given `?user_id=`.                                                      |

---

### ⚡ WebSocket — Real-Time Telemetry

| Protocol    | Endpoint              | Description                                                                                          |
|-------------|-----------------------|------------------------------------------------------------------------------------------------------|
| `WebSocket` | `/ws/robot/{robot_id}` | Subscribe to live telemetry for a specific robot. The server broadcasts the full `RobotStatusOut` JSON object to all connected clients on every successful `POST /api/robot-status` heartbeat. |

**Connection Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/robot/shelloc-01');
ws.onmessage = (event) => {
  const telemetry = JSON.parse(event.data);
  console.log('Live update:', telemetry.mission_state, telemetry.current_lat);
};
```

---

## Running the Simulation

A robot simulator is included for local development and testing without physical hardware.

```bash
# With the uvicorn server already running:
python scripts/simulate_robot.py
```

The simulator runs a full 9-stage mission cycle automatically, posting realistic telemetry data to the local backend at each stage. Use this to test the dashboard UIs end-to-end.

---

## Documentation Directory

| Document                                                 | Description                                                                         |
|----------------------------------------------------------|-------------------------------------------------------------------------------------|
| [docs/architecture.md](./docs/architecture.md)           | Complete architectural blueprint, 9-state FSM, data flow, and edge responsibilities. |
| [docs/data-model.md](./docs/data-model.md)               | Canonical Pydantic v2 schemas, MongoDB collections, and status matrix.              |
| [docs/implementation-spec.md](./docs/implementation-spec.md) | Internal business rules, edge timer coordination, and failsafe behavior.        |
| [docs/api-reference.md](./docs/api-reference.md)         | Extended endpoint reference, payloads, and WebSocket specifications.                |
| [docs/development-guide.md](./docs/development-guide.md) | Docker workflows, simulator usage, and deployment configuration.                    |
