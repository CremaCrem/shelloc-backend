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

1. **Before a mission:** App user creates up to 6 **waypoints** (GPS coordinates) for the robot to visit.
2. **During a mission:** Robot navigates autonomously between waypoints, sends **sensor readings** (before and after treatment) and **robot status** heartbeats via GPRS. The mobile app updates its live telemetry dashboards by HTTP polling `GET /api/robot-status/{id}` and `GET /api/sensor-readings/latest` at a 5-second interval.
3. **During treatment:** Robot disperses Moringa-Chitosan flocculant, then logs a **treatment event** (dosage, aggregation time, pollution level).
4. **Anytime:** App user can open the **AI chat** to ask questions about water quality in plain language.

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

## 6. AI Service Design

The AI interprets sensor data and treatment outcomes for non-technical users. 

### Context Building
The AI service (`services/ai_service.py`) queries MongoDB and builds a compact context summary including:
- Latest robot status
- Latest sensor reading per waypoint
- Any critical waypoints

### Provider Strategy
The backend supports multiple AI providers (OpenAI, Claude, Gemini) configured via `AI_PROVIDER`. At this scale, a simple `if/elif` block inside `ai_service.py` is sufficient—do not introduce complex abstraction/plugin architectures unless the codebase requires it.
