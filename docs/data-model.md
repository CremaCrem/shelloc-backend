# Data Model Schema Reference

This document provides the canonical schema reference for all Pydantic v2 data models and MongoDB document structures within the SHELLOC backend.

## Conventions

- **`id`**: MongoDB ObjectId serialized to a 24-character hexadecimal string.
- **`robot_id`**: String identifier for the physical robot (e.g., `"SHELLOC-01"`).
- **`waypoint_id`**: String referencing a valid waypoint document ID.
- **Server-set fields**: Computed or timestamped by the server. Cannot be overwritten by clients.
- **Optional fields**: Default to `None` unless explicitly noted.

---

## 1. Sensor Readings (`sensor_readings`)

Stores water quality telemetry snapshots captured by the robot before and after remediation cycles.

### Request Schema (`SensorReadingCreate`)

| Field | Type | Required | Description |
|---|---|---|---|
| `robot_id` | `str` | Yes | Unique identifier of the reporting robot |
| `waypoint_id` | `str` | Yes | ObjectId string of the associated waypoint |
| `phase` | `Literal["before", "after"]` | Yes | Reading taken prior to dosing or post-remediation |
| `turbidity_ntu` | `float` | Yes | Water turbidity in Nephelometric Turbidity Units (NTU) |
| `ph` | `float` | Yes | Acidity / alkalinity index (0.0 – 14.0 scale) |
| `tds_ppm` | `float` | Yes | Total Dissolved Solids in parts per million (ppm) |
| `temperature_celsius` | `float` | No | Water temperature in degrees Celsius (°C) |
| `nir_floc_score` | `float` | No | Near-Infrared optical floc aggregation index (0.0 – 1.0) |
| `obstacle_detected` | `bool` | No | Boolean flag indicating SONAR underwater object proximity |
| `sonar_distance_cm` | `float` | No | Distance to nearest underwater object in centimeters |

### Response Schema (`SensorReadingOut`)

All request fields, plus:

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | MongoDB `_id` serialized as string |
| `timestamp` | `datetime` | _(server-set)_ UTC creation timestamp |
| `status` | `Literal["good", "borderline", "critical", "no_data"]` | _(server-set)_ Multi-parameter water health evaluation |

#### Status Computation Matrix:
- **`"good"`**: `turbidity_ntu < 20` AND `6.0 <= ph <= 7.5`
- **`"borderline"`**: `20 <= turbidity_ntu <= 50` OR `(5.5 <= ph < 6.0)` OR `(7.5 < ph <= 8.5)`
- **`"critical"`**: `turbidity_ntu > 50` OR `ph < 5.5` OR `ph > 8.5`

---

## 2. Waypoints (`waypoints`)

Stores mission coordinates and treatment status for up to 6 targets per robot.

### Request Schema (`WaypointCreate`)

| Field | Type | Required | Description |
|---|---|---|---|
| `robot_id` | `str` | Yes | Associated robot identifier |
| `point_number` | `int` | Yes | 1-based target index (1 to 6) |
| `latitude` | `float` | Yes | GPS latitude in decimal degrees |
| `longitude` | `float` | Yes | GPS longitude in decimal degrees |
| `label` | `str` | No | Custom label (defaults to `"Point {point_number}"`) |
| `radius_meters` | `float` | No | Geofence arrival boundary radius (default `2.0` meters) |

### Update Schema (`WaypointUpdate`)

| Field | Type | Notes |
|---|---|---|
| `treated` | `bool` | Set to `true` upon successful remediation cycle completion |
| `before_reading_id` | `str` | ObjectId of the baseline sensor reading |
| `after_reading_id` | `str` | ObjectId of the post-treatment sensor reading |
| `treated_at` | `datetime` | UTC timestamp of completion |

### Response Schema (`WaypointOut` & `WaypointDetailOut`)

`WaypointOut` returns all create/update fields with `id` and `created_at`.  
`WaypointDetailOut` inlines the full `before_reading` and `after_reading` objects to eliminate extra client round-trips.

---

## 3. Robot Status (`robot_status`)

Single living document per robot upserted on every heartbeat (5-second interval).

### Request Schema (`RobotStatusUpdate`)

| Field | Type | Required | Description |
|---|---|---|---|
| `operation_mode` | `Literal["autonomous", "manual"]` | Yes | Operational navigation mode |
| `gps_signal` | `Literal["good", "weak", "none"]` | No | GPS satellite lock quality |
| `current_lat` | `float` | No | Current latitude coordinate |
| `current_lng` | `float` | No | Current longitude coordinate |
| `battery_percent` | `int` | Yes | Battery state of charge (0 – 100%) |
| `points_treated_today` | `int` | No | Number of targets remediated in current session |
| `target_waypoint_id` | `str \| None` | No | ObjectId of the target waypoint the robot is dispatched to |
| `mission_state` | `Literal[...]` | No | Current state in the 9-state closed-loop lifecycle (see below) |
| `flocculant_tank_percent` | `int` | No | Moringa-Chitosan reagent reservoir level (0 – 100%) |
| `citric_acid_tank_percent` | `int` | No | Citric Acid reagent reservoir level (0 – 100%) |
| `biochar_health_status` | `Literal["optimal", "degraded", "replace"]` | No | Health / absorption capacity of biochar filter |
| `timer_remaining_sec` | `int \| None` | No | Remaining seconds on the 15-minute incubation timer |
| `buoyancy_failsafe_active` | `bool` | No | Active status of ballast evacuation pump for GPS recovery |

#### Mission State Enum Values:
- `"idle"`: Awaiting target dispatch
- `"navigating"`: En route to target waypoint
- `"baseline_evaluating"`: Inside 2m boundary, reading baseline parameters
- `"dispensing_flocculant"`: Pumping adaptive Moringa-Chitosan dosage
- `"incubating_15m"`: 15-minute macro-floc aggregation countdown active
- `"mesh_biochar_filtering"`: Maneuvering to filter flocs and absorb dissolved ions
- `"post_evaluating"`: Reading post-treatment parameters
- `"adaptive_stabilization"`: Dispensing Citric Acid (pH) or secondary flocculant (NTU)
- `"completed"`: Remediation finished for active target
- `"failsafe_buoyancy"`: GPS signal lost; pumping ballast water to regain satellite lock

### Response Schema (`RobotStatusOut`)

All update fields, plus:

| Field | Type | Notes |
|---|---|---|
| `robot_id` | `str` | Path param used as primary document key |
| `last_sync` | `datetime` | _(server-set)_ UTC timestamp of last heartbeat |
| `overall_status` | `str` | _(server-set)_ `"operational"`, `"low_battery"`, `"gps_lost"`, `"buoyancy_failsafe"`, or `"degraded"` |

---

## 4. Treatment Events (`treatment_events`)

Comprehensive historical log recording every closed-loop remediation cycle.

### Request Schema (`TreatmentEventCreate`)

| Field | Type | Required | Description |
|---|---|---|---|
| `robot_id` | `str` | Yes | Reporting robot ID |
| `waypoint_id` | `str` | Yes | Target waypoint ObjectId string |
| `pollution_level` | `Literal["low", "medium", "high"]` | Yes | Classified pollution tier (Low: 20-50, Med: 50-120, High: 120-200 mg/L) |
| `flocculant_dosed_ml` | `float` | Yes | Primary Moringa-Chitosan volume dispensed (mL) |
| `citric_acid_dosed_ml` | `float` | No | Citric Acid volume dispensed for pH stabilization (mL, default `0.0`) |
| `biochar_filtration_applied`| `bool` | No | Whether biochar cartridge and mesh sweep completed (default `True`) |
| `floc_aggregation_time_sec`| `int` | No | Duration of flocculation incubation (default `900` seconds / 15 mins) |
| `secondary_treatment_applied`| `bool` | No | Flag indicating if adaptive post-treatment dosing was required |
| `secondary_reagent_type` | `Literal["flocculant", "citric_acid"] \| None` | No | Reagent used in secondary cycle |
| `secondary_dosage_ml` | `float \| None` | No | Volume used in secondary cycle (mL) |
| `eta_next_area_sec` | `int \| None` | No | Estimated transit time to next waypoint |

### Response Schema (`TreatmentEventOut`)

All create fields, plus:

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | MongoDB `_id` serialized as string |
| `started_at` | `datetime` | _(server-set)_ UTC cycle initiation timestamp |
| `ended_at` | `datetime \| None` | UTC cycle completion timestamp |
| `outcome` | `Literal["remediated", "stabilized", "recollection_needed", "flagged_manual"] \| None` | Remediation result classification |

---

## 5. AI Chat Logs (`ai_chat_logs`)

Maintains conversational state and domain context between the user and Google Gemini.

### Request Schema (`ChatMessageCreate`)

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | `str` | Yes | Client session identifier |
| `robot_id` | `str` | Yes | Target robot for context snapshot grounding |
| `message` | `str` | Yes | User inquiry or diagnostic request |

### Response Schema (`ChatMessageOut`)

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | MongoDB `_id` as string |
| `role` | `Literal["user", "assistant"]` | Message author |
| `message` | `str` | Text content (Markdown supported) |
| `timestamp` | `datetime` | _(server-set)_ UTC timestamp |
| `context_snapshot` | `dict \| None` | Injected telemetry snapshot for assistant messages |
