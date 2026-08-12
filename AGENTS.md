# SHELLOC Backend — Agent Context

## Source of Truth Matrix

When you are acting as an AI coding agent or IDE agent on this repository, you must use the following documents to determine how the project works. **Do not invent field names, endpoints, or requirements that are not listed here.**

| Question | Source of truth |
|---|---|
| What is SHELLOC? | [README.md](./README.md) |
| How is the system structured? | [docs/architecture.md](./docs/architecture.md) |
| What API endpoints exist? | [docs/api-reference.md](./docs/api-reference.md) |
| What fields/types exist? | [docs/data-model.md](./docs/data-model.md) |
| How should backend behavior work? | [docs/implementation-spec.md](./docs/implementation-spec.md) |
| How do I develop/run/test it? | [docs/development-guide.md](./docs/development-guide.md) |
| How should an AI coding agent behave? | [AGENTS.md](./AGENTS.md) (this file) |

## Core Operational Rules

1. **Stack**: FastAPI (async), Motor (async MongoDB driver), Pydantic v2.
2. **API Conventions**: All routes prefixed `/api`. 
3. **Authentication Boundaries**: Robot-facing write endpoints (`POST /api/sensor-readings`, `POST /api/robot-status/{id}`, `POST /api/treatment-events`) require the `X-API-Key` header via the `auth.verify_api_key` dependency. App-facing reads and `/api/ai-chat` do NOT require auth.
4. **Server-Computed Fields**: The backend must compute certain fields like `timestamp`, `status` (for readings), `last_sync`, and `overall_status` (for robot). Never trust these fields if sent by the client. See `docs/implementation-spec.md` for exact logic.
5. **Error Handling**: Return `404` for missing resources and `400` for invalid `ObjectId` strings. Do not leak raw `500` errors for bad user input.
6. **Code Organization**: Keep routers thin. Put complex logic, computed fields, and AI provider calls in `services/`.
7. **Database Operations**: Do NOT cascade-delete historical data (readings, treatment events) when a waypoint is deleted. Keep historical data and simply unlink.
8. **AI Provider Architecture**: Do not abstract the AI provider behind a plugin interface. A simple `if/elif` block checking `config.AI_PROVIDER` is sufficient.

## Build Order

When building from scratch, follow this exact order:
1. `core/config.py` & `core/database.py`
2. `sensor_readings` (schema, model, router)
3. `waypoints`
4. `robot_status`
5. `treatment_events`
6. `core/auth.py`
7. `services/ai_service.py` & `ai_chat` router
8. `main.py` wiring & verification

## Things NOT to do
- Do not add authentication for app users (out of scope).
- Do not introduce unnecessary abstractions (e.g., repository patterns, generic CRUD factories, dependency injection frameworks). This is a student research backend and must remain understandable.
- Do not silently redesign exact turbidity thresholds or existing field names. Follow `docs/data-model.md` and `docs/implementation-spec.md`.