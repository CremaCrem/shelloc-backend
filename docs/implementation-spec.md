# Implementation Specification

This file specifies HOW the backend must behave internally: validation rules, computed fields, business logic, and error handling. For endpoint definitions, see `api-reference.md`. For schema details, see `data-model.md`.

## 1. Core Behavior

### Configuration (`core/config.py`)
- Load environment variables once via `python-dotenv`.
- Expose a single `Settings` object.
- **Fail at startup** (raise error) if `MONGO_URI`, `DB_NAME`, `API_KEY`, `AI_PROVIDER`, or `AI_API_KEY` are missing.

### Database (`core/database.py`)
- Create the Motor async database connection once at module load (single client), not per-request.
- Expose `get_database()`.

### Authentication (`core/auth.py`)
- Define a FastAPI dependency `verify_api_key` that checks the incoming `X-API-Key` header against `config.API_KEY`.
- Return `401 Unauthorized` on mismatch.
- Apply ONLY to robot write endpoints (`POST /api/sensor-readings`, `POST /api/robot-status/{id}`, `POST /api/treatment-events`).

### Error Handling
- Use `HTTPException` appropriately.
- Invalid `ObjectId` strings in path/query params MUST return `400 Bad Request`, not crash with a `500`. (Use `bson.ObjectId` and catch `bson.errors.InvalidId`).
- Missing resources (e.g., getting a non-existent waypoint) MUST return `404 Not Found` with a clear message.

## 2. Status Computation Rules (Server-Computed)

These fields are **always computed by the server**. Ignore or override any client-submitted values for these fields.

### Sensor Reading `status`
Computed from `turbidity_ntu` at insert time:
- `turbidity_ntu < 20` → `"good"`
- `20 ≤ turbidity_ntu ≤ 50` → `"borderline"`
- `turbidity_ntu > 50` → `"critical"`

### Robot Status `overall_status`
Computed from `battery_percent`, `gps_signal`, and `operation_mode`:
- Battery ≥ 20% and GPS good/weak → `"operational"`
- Battery < 20% → `"low_battery"`
- GPS none → `"gps_lost"`
- Multiple issues → `"degraded"`

## 3. Router Behavior

Keep routers thin. They should: parse input, call the database/services, and format responses.

### Sensor Readings
- **Validation**: Verify `waypoint_id` exists before inserting. Return `404` if not found.
- **Latest readings**: The `/latest` endpoint (given `robot_id`) queries the single most recent reading per waypoint. Used for map color-coding.

### Waypoints
- **Constraints**: Enforce max **6 waypoints per `robot_id`** on POST. Return `400` if exceeded.
- **Inlining**: `GET /{id}` should fetch the full `before_reading` and `after_reading` documents (if linked) and include them in the response.
- **Deletion**: When deleting a waypoint, do NOT cascade-delete historical sensor readings or treatment events. Unlink references if needed, but preserve the historical documents.

### Robot Status
- **Upsert**: The POST endpoint should UPSERT the document using the path param `robot_id` as the key.
- Update `last_sync` to current server time on every upsert.

### Treatment Events
- **Validation**: Verify `waypoint_id` exists before inserting. Return `404` if not found.
- **Timestamps**: Set `started_at` to server time on create. `ended_at` and `outcome` are currently nullable and out of scope for v1 (to be added via future PATCH).

### AI Chat
- Flow for `POST /api/ai-chat`:
  1. Save user message to `ai_chat_logs`.
  2. Call `ai_service.build_context(robot_id)` to get compact data.
  3. Call `ai_service.get_ai_reply(message, context)` to call provider.
  4. Save assistant reply with `context_snapshot`.
  5. Return assistant message.

## 4. Open Decisions

> [!WARNING]
> The following items are currently unspecified or have conflicting interpretations in the existing specifications. If modifying these areas, check the existing codebase for precedence or seek clarification.

- **Treatment Event Lifecycle**: Currently, `POST /treatment-events` creates an event. `ended_at` and `outcome` are null. It is undetermined whether the robot sends a subsequent `PATCH` or if it sends a complete event after it finishes. For v1, simple insertion is sufficient.
- **App-User Authentication**: No app-facing authentication exists. Do not implement JWT or user accounts unless specifically requested.

## 5. Implementation Build Order
When implementing the backend from scratch, follow this order:
1. `core/config.py` → `core/database.py`
2. `sensor_readings` (schemas, models, router)
3. `waypoints`
4. `robot_status`
5. `treatment_events`
6. `core/auth.py`
7. `services/ai_service.py` & `ai_chat` router
8. `main.py` wiring
