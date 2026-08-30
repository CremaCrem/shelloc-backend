# API Reference

All routes are prefixed with `/api`.  
Every list endpoint accepts a `limit` query parameter (default `50`, maximum `200`).  
Robot write endpoints require authentication via `X-API-Key` header.

---

## 1. Sensor Readings

**Base Path:** `/api/sensor-readings`

| Method | Path | Auth | Request Body | Description |
|---|---|---|---|---|
| `POST` | `/` | `X-API-Key` | `SensorReadingCreate` | Submit baseline (`before`) or remediated (`after`) water quality reading. Server computes `status` from NTU and pH. |
| `GET` | `/` | None | Query: `robot_id`, `waypoint_id`, `limit` | List sensor readings in reverse chronological order. |
| `GET` | `/{id}` | None | None | Retrieve single sensor reading document by ID. |
| `GET` | `/latest` | None | Query: `robot_id` | Returns the single most recent reading per waypoint for the specified robot. |

### Payload Attributes (`SensorReadingCreate`)
- `robot_id` (`str`), `waypoint_id` (`str`), `phase` (`"before" | "after"`)
- `turbidity_ntu` (`float`), `ph` (`float`), `tds_ppm` (`float`)
- `temperature_celsius` (`float`, optional)
- `nir_floc_score` (`float`, optional)
- `obstacle_detected` (`bool`, optional), `sonar_distance_cm` (`float`, optional)

---

## 2. Waypoints

**Base Path:** `/api/waypoints`

| Method | Path | Auth | Request Body | Description |
|---|---|---|---|---|
| `POST` | `/` | None | `WaypointCreate` | Create a target waypoint (maximum 6 per `robot_id`). |
| `GET` | `/` | None | Query: `robot_id`, `limit` | List all waypoints for a robot. |
| `GET` | `/{id}` | None | None | Get waypoint details with inlined `before_reading` and `after_reading` objects. |
| `PATCH`| `/{id}` | None | `WaypointUpdate` | Update waypoint state (mark `treated: true`, link reading IDs). |
| `DELETE`| `/{id}`| None | None | Delete waypoint. Preserves linked historical readings and events. |

---

## 3. Robot Status & Telemetry

**Base Path:** `/api/robot-status`

| Method | Path | Auth | Request Body | Description |
|---|---|---|---|---|
| `POST` | `/{robot_id}` | `X-API-Key` | `RobotStatusUpdate` | Ingest robot heartbeat. Computes `overall_status`, updates `last_sync`, and broadcasts payload to active WebSockets. |
| `GET` | `/{robot_id}` | None | None | Retrieve latest robot telemetry, active target waypoint, and mission state. |
| `PATCH`| `/{robot_id}` | None | `RobotStatusDispatch` | Dispatch robot to a target waypoint (`target_waypoint_id`). Set `null` to cancel target. |

### Payload Attributes (`RobotStatusUpdate`)
- `operation_mode` (`"autonomous" | "manual"`), `battery_percent` (`0-100`)
- `gps_signal` (`"good" | "weak" | "none"`), `current_lat` (`float`), `current_lng` (`float`)
- `mission_state` (`"idle" | "navigating" | "baseline_evaluating" | "dispensing_flocculant" | "incubating_15m" | "mesh_biochar_filtering" | "post_evaluating" | "adaptive_stabilization" | "completed" | "failsafe_buoyancy"`)
- `flocculant_tank_percent` (`int`), `citric_acid_tank_percent` (`int`), `biochar_health_status` (`str`)
- `timer_remaining_sec` (`int`, optional)
- `buoyancy_failsafe_active` (`bool`, optional)

---

## 4. Treatment Events

**Base Path:** `/api/treatment-events`

| Method | Path | Auth | Request Body | Description |
|---|---|---|---|---|
| `POST` | `/` | `X-API-Key` | `TreatmentEventCreate` | Log a closed-loop treatment cycle (reagents dispensed, incubation timing, biochar filtration). |
| `GET` | `/` | None | Query: `robot_id`, `waypoint_id`, `limit` | List treatment logs sorted newest first. |
| `GET` | `/{id}` | None | None | Retrieve single treatment event details. |

### Payload Attributes (`TreatmentEventCreate`)
- `robot_id` (`str`), `waypoint_id` (`str`)
- `pollution_level` (`"low" | "medium" | "high"`)
- `flocculant_dosed_ml` (`float`), `citric_acid_dosed_ml` (`float`, default `0.0`)
- `biochar_filtration_applied` (`bool`, default `True`)
- `floc_aggregation_time_sec` (`int`, default `900`)
- `secondary_treatment_applied` (`bool`, default `False`)
- `secondary_reagent_type` (`"flocculant" | "citric_acid"`, optional)
- `secondary_dosage_ml` (`float`, optional)

---

## 5. AI Chat (Google Gemini)

**Base Path:** `/api/ai-chat`

| Method | Path | Auth | Request Body | Description |
|---|---|---|---|---|
| `POST` | `/` | None | `ChatMessageCreate` | Send a query to the Google Gemini engine (`gemini-3.7-flash`). Injects grounded telemetry snapshot and returns conversational remediation advice. |
| `GET` | `/history` | None | Query: `user_id`, `limit` | Fetch conversational history for the given user session. |

---

## 6. Real-Time Telemetry (WebSockets)

**Base Path:** `/ws/robot`

| Protocol | Path | Auth | Description |
|---|---|---|---|
| `WebSocket` | `/{robot_id}` | None | Open a persistent stream to receive instant JSON broadcasts of `RobotStatusOut` whenever the robot publishes a heartbeat or transitions mission state. |
