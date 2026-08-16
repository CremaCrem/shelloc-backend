# Architecture Overview

This document explains HOW the SHELLOC backend system is organized.

## 1. System Context

**SHELLOC** (Smart Hydro-Environmental Locator and Cleaner) is an autonomous water-remediation robot that deploys Moringa-Chitosan flocculant to treat suspended particulate matter (SPM) in open water bodies.

### System Components

```mermaid
flowchart TD
    subgraph Robot Hardware
        Matrix[MATRIX Mini R4 / Raspberry Pi]
        Sensors[Turbidity, pH, TDS, NIR camera]
        GPS[SIM808 GPS/GPRS]
        Pump[Moringa-Chitosan pump]
    end

    subgraph React Native Expo App
        Dash[Live sensor dashboards]
        Map[Waypoint map]
        Chat[AI chat]
    end

    Backend[FastAPI Backend]
    DB[(MongoDB)]
    AI[AI Provider: OpenAI/Claude/Gemini]

    Robot Hardware -- GPRS POST --> Backend
    React Native Expo App -- REST GET/PATCH --> Backend
    Backend <--> DB
    Backend <--> AI
```

### Data Flow Summary

1. **Setup:** App user creates up to 6 **waypoints** (GPS coordinates with a fixed 2-meter radius boundary zone) for the robot's mission area.
2. **Dispatch:** App user selects a single active target waypoint and dispatches the robot to it via `PATCH /api/robot-status/{robot_id}` with `target_waypoint_id`. The robot operates **one waypoint at a time**.
3. **Navigation (Real-Time Telemetry):** Robot autonomously self-navigates toward the target waypoint coordinates. It sends **robot status** heartbeats via GPRS containing its current GPS position and `mission_state`. The mobile app establishes a **WebSocket connection** (`/ws/robot/{robot_id}`) to instantly receive these live telemetry broadcasts without needing to poll.
4. **Arrival (2m Boundary):** When the robot's GPS position is within **2 meters** of the waypoint center, it enters `"inside_boundary"` mission state and begins the treatment cycle.
5. **Treatment:** Inside the 2m zone, the robot takes a `before` sensor reading, disperses Moringa-Chitosan flocculant, waits for aggregation, then takes an `after` sensor reading. A **treatment event** is logged with dosage, aggregation time, and pollution level. The waypoint is marked `treated = True`.
6. **Completion:** `mission_state` returns to `"idle"`. The user may then dispatch the robot to another waypoint.
7. **Anytime:** App user can open the **AI chat** to ask questions about water quality in plain language.

## 2. Folder Structure

```text
app/
├── main.py          # App factory: creates FastAPI instance, includes all routers
├── core/            # Infrastructure and configuration
│   ├── config.py    # Reads .env, exposes Settings object
│   ├── database.py  # Motor client; exposes get_database()
│   └── auth.py      # verify_api_key FastAPI dependency
├── models/          # Python dataclasses / TypedDicts describing raw Mongo documents
├── schemas/         # Pydantic v2 models for request validation & response serialization
├── routers/         # FastAPI APIRouter instances — thin, delegate logic to services/
├── services/        # Business logic and AI service implementation
└── utils/           # Shared utilities
```

## 3. Layer Responsibilities

- **core/**: Handles database connections, environment configuration, and authentication dependencies.
- **models/**: Defines the raw shape of documents as they exist in MongoDB.
- **schemas/**: Defines Pydantic models for request body validation and response serialization.
- **routers/**: HTTP/API layer. Routes should be thin, delegating heavy logic to `services/`.
- **services/**: Contains business logic, AI provider integration, and any complex computed behavior.
- **utils/**: Contains generic helpers (e.g., ObjectId string conversion).

## 4. Authentication Boundaries

- **Robot write endpoints** (`POST /api/sensor-readings`, `POST /api/robot-status/{id}`, `POST /api/treatment-events`) require an `X-API-Key` header.
- **App-facing reads and AI chat** are currently unauthenticated. (App-user authentication is out of scope for now).

## 5. Database Relationships

| Collection | Purpose | Key indexes |
|---|---|---|
| `sensor_readings` | One doc per sensor snapshot (before or after treatment) | `robot_id`, `waypoint_id`, `timestamp` descending |
| `waypoints` | GPS treatment points, up to 6 per robot | `robot_id` |
| `robot_status` | One doc per robot (upserted on each heartbeat) | `robot_id` unique |
| `treatment_events` | One doc per flocculation treatment cycle | `robot_id`, `waypoint_id` |
| `ai_chat_logs` | User and assistant messages | `user_id`, `timestamp` ascending |

### Notes on Data Relationships
- A `sensor_reading` links to a `waypoint` via `waypoint_id` (ObjectId string).
- A `waypoint` stores `before_reading_id` and `after_reading_id` — these are updated via `PATCH /api/waypoints/{id}` after readings are created.
- `GET /api/waypoints/{id}` resolves and inlines the referenced reading objects so the app avoids a second round-trip.
- **Deleting a waypoint does not cascade-delete readings or treatment events** — historical data is preserved, references are simply unlinked.
- `robot_status` tracks the currently active `target_waypoint_id` and `mission_state` so both the hardware and mobile app share a single source of truth on which waypoint is being serviced and the robot's progress toward it.

## 6. AI Service Design

The AI interprets sensor data and treatment outcomes for non-technical users. 

### Context Building
The AI service (`services/ai_service.py`) queries MongoDB and builds a compact context summary including:
- Latest robot status
- Latest sensor reading per waypoint
- Any critical waypoints

### Provider Implementation
The backend integrates with Google Gemini using the official `google-genai` SDK (targeting `gemini-3.7-flash`). While `AI_PROVIDER` configuration exists for multi-provider extensibility, OpenAI and Claude currently remain **unimplemented placeholders**.

### Multi-Turn Conversational Memory
To maintain chat context without unbounded token growth, `ai_service.py` queries `db.ai_chat_logs` for the most recent `MAX_CHAT_HISTORY` (configured to `5`) messages for the requesting `user_id`. These past exchanges are converted to `types.Content` objects (with `"user"` and `"model"` roles) and prepended to the Gemini generation request.

### System Instruction & Domain Grounding
The AI model is guided by a comprehensive `SYSTEM_INSTRUCTION` that grounds its responses in research-backed water quality standards:
- **Turbidity (NTU):** `< 20 NTU` = good/remediated (monitoring only); `20–50 NTU` = borderline; `> 50 NTU` = critical/severe (requires active treatment). Untreated baseline is typically 110.33–146.51 NTU, and post-treatment target is 10.40–16.25 NTU.
- **pH:** `< 6.0` = acidic/degraded (requires stabilization); `6.0–7.0` = target stabilized post-treatment window (mean ~6.46); `> 7.5–8.5` = borderline/elevated alkaline. Untreated baseline is typically 4.95–6.03.
- **TDS (ppm):** `> 400 ppm` = high dissolved particulate load; `~200–250 ppm` = target remediated state. Untreated baseline is typically 394.16–485.13 ppm, and post-treatment target is 197.16–243.12 ppm.
- **Flocculant Dosage (Moringa-Chitosan):** Adaptive dosage based on turbidity. If `< 20 NTU`: no additional flocculant, monitoring only. If `20–50 NTU`: moderate dosage via pump. If `> 50 NTU` (or baseline `> 100 NTU`): full/maximum standard dosage for rapid macro-floc aggregation.
- **Geofence Boundary:** 2-meter radius from the target waypoint.

Concrete recommendations (such as dosage adjustments or status verdicts) are explicitly structured with bold callouts (e.g., `**Recommendation:** ...`) for readability.

### Error Handling & Resilience
External AI calls are wrapped in exception handlers. If the Gemini API call fails due to invalid credentials, rate limiting, or network unavailability, `ai_service.py` catches the error and returns a formatted Markdown error message (`**Error:** ...`) instead of raising an unhandled exception. This ensures the `/api/ai-chat/` endpoint never returns a `500 Internal Server Error` due to upstream AI provider failures.
