# API Reference

All routes are prefixed with `/api`.
Every list endpoint accepts `limit` (default 50, max 200).
Every `GET /{id}` returns `404` with a descriptive message if not found.
Every `POST` (create) returns `201` with the created object including server-generated `id`.
Invalid ObjectId strings in path/query params return `400`.

## 1. Sensor Readings

**Path prefix:** `/api/sensor-readings`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/` | `X-API-Key` | Create a new sensor reading. Computes status server-side. |
| `GET` | `/` | None | List readings. Query params: `robot_id`, `waypoint_id`, `limit`. |
| `GET` | `/{id}` | None | Get a single reading. |
| `GET` | `/latest`| None | Query param: `robot_id`. Returns the single most recent reading per waypoint for the robot. |

## 2. Waypoints

**Path prefix:** `/api/waypoints`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/` | None | Create a waypoint. Max 6 per `robot_id` (returns `400` if exceeded). |
| `GET` | `/` | None | List waypoints. Query params: `robot_id`. |
| `GET` | `/{id}` | None | Get waypoint. Returns inlined `before_reading` and `after_reading` objects. |
| `PATCH` | `/{id}` | None | Partial update (e.g., link readings, set treated status). |
| `DELETE`| `/{id}` | None | Delete waypoint. Does NOT cascade-delete historical readings or events. |

## 3. Robot Status

**Path prefix:** `/api/robot-status`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/{robot_id}` | `X-API-Key` | Upsert robot heartbeat. Computes `overall_status` server-side. |
| `GET` | `/{robot_id}` | None | Get latest robot status. Returns `404` if no heartbeat ever received. |

## 4. Treatment Events

**Path prefix:** `/api/treatment-events`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/` | `X-API-Key` | Log a treatment cycle. `started_at` is set server-side. |
| `GET` | `/` | None | List events. Query params: `robot_id`, `waypoint_id`, `limit`. |
| `GET` | `/{id}` | None | Get a single event. |

## 5. AI Chat

**Path prefix:** `/api/ai-chat`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/` | None | Send a message. Returns AI assistant reply with context snapshot. |
| `GET` | `/history` | None | Query param: `user_id`, `limit`. List messages in chronological order. |
