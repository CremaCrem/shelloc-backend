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
2. **API Conventions**: All routes prefixed `/api`. Real-time telemetry streamed via `/ws/robot/{robot_id}`.
3. **Authentication Boundaries**: Robot-facing write endpoints (`POST /api/sensor-readings`, `POST /api/robot-status/{id}`, `POST /api/treatment-events`) require the `X-API-Key` header via the `auth.verify_api_key` dependency. App-facing reads and `/api/ai-chat` do NOT require auth.
4. **Server-Computed Fields**: The backend must compute certain fields like `timestamp`, `status` (for readings using combined NTU and pH rules), `last_sync`, and `overall_status` (for robot including buoyancy failsafe). Never trust these fields if sent by the client. See `docs/implementation-spec.md` for exact logic.
5. **Closed-Loop State Machine**: Support the 9-state lifecycle (`idle`, `navigating`, `baseline_evaluating`, `dispensing_flocculant`, `incubating_15m`, `mesh_biochar_filtering`, `post_evaluating`, `adaptive_stabilization`, `completed`) and `failsafe_buoyancy`.
6. **Dual Reagents & Consumables**: Track both Moringa-Chitosan flocculant and Citric Acid pH stabilizer volumes in treatment events and reservoir percentages in robot status.
7. **Error Handling**: Return `404` for missing resources and `400` for invalid `ObjectId` strings. Do not leak raw `500` errors for bad user input.
8. **Code Organization**: Keep routers thin. Put complex logic, computed fields, and AI provider calls in `services/`.
9. **Database Operations**: Do NOT cascade-delete historical data (readings, treatment events) when a waypoint is deleted. Keep historical data and simply unlink.
10. **AI Engine**: Use Google Gemini (`gemini-3.7-flash` via `google-genai` SDK) as the active conversational engine for plain-language telemetry interpretation and remediation science.

## Things NOT to do
- Do not add authentication for app users (out of scope).
- Do not introduce unnecessary abstractions (e.g., repository patterns, generic CRUD factories, complex dependency injection frameworks).
- Do not replace Google Gemini with other providers.
- Follow `docs/data-model.md` and `docs/implementation-spec.md` for exact field names and validation rules.