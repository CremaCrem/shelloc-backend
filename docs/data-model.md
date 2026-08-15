# Data Model Schema Reference

Quick-reference for all Pydantic schema classes and MongoDB document structures. For full behavioral specs (computed fields, validation rules), see `implementation-spec.md`.

## Conventions

- **`id`**: always a `str` (MongoDB ObjectId serialized to string) in response schemas.
- **`robot_id`**: plain string identifier for the robot.
- **`waypoint_id`**: MongoDB ObjectId string referencing a waypoint document.
- **Server-set fields**: marked with _(server-set)_. Never trust these from client input.
- **Optional fields** default to `None` unless otherwise noted.

## 1. Sensor Readings

### Request Schema (`SensorReadingCreate`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `robot_id` | `str` | yes | |
| `waypoint_id` | `str` | yes | ObjectId string; validated to exist |
| `phase` | `Literal["before", "after"]` | yes | Reading taken before or after treatment |
| `turbidity_ntu` | `float` | yes | NTU units |
| `ph` | `float` | yes | pH scale 0–14 |
| `tds_ppm` | `float` | yes | Total dissolved solids in ppm |
| `nir_floc_score` | `float` | no | Default `None`; NIR-derived floc aggregation score |

### Response Schema (`SensorReadingOut`)
All request fields, plus:
| Field | Type | Notes |
|---|---|---|
| `id` | `str` | MongoDB `_id` as string |
| `timestamp` | `datetime` | _(server-set)_ UTC insert time |
| `status` | `Literal["good", "borderline", "critical", "no_data"]` | _(server-set)_ computed from `turbidity_ntu` |

## 2. Waypoints

### Request Schema (`WaypointCreate`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `robot_id` | `str` | yes | |
| `point_number` | `int` | yes | 1-based index |
| `latitude` | `float` | yes | Decimal degrees |
| `longitude` | `float` | yes | Decimal degrees |
| `label` | `str` | no | Defaults to `f"Point {point_number}"` |
| `radius_meters` | `float` | no | Boundary radius around the waypoint center. Defaults to `2.0`. The robot must be within this radius to begin treatment. |

### Update Schema (`WaypointUpdate`)
All optional:
| Field | Type |
|---|---|
| `treated` | `bool` |
| `before_reading_id` | `str` |
| `after_reading_id` | `str` |
| `treated_at` | `datetime` |

### Response Schema (`WaypointOut`)
All create fields, plus:
| Field | Type | Notes |
|---|---|---|
| `id` | `str` | MongoDB `_id` as string |
| `treated` | `bool` | Default `False` |
| `created_at` | `datetime` | _(server-set)_ |
| `treated_at` | `datetime \| None` | Nullable until treated |
| `before_reading_id` | `str \| None` | ObjectId string, nullable |
| `after_reading_id` | `str \| None` | ObjectId string, nullable |
| `radius_meters` | `float` | Boundary radius (defaults to `2.0`). Passed through from create. |

> **Note:** `GET /api/waypoints/{id}` returns this schema with `before_reading` and `after_reading` objects **inlined**. List endpoints return IDs only.

## 3. Robot Status

### Request Schema (`RobotStatusUpdate`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `operation_mode` | `Literal["autonomous", "manual"]` | yes | |
| `gps_signal` | `Literal["good", "weak", "none"]` | no | |
| `current_lat` | `float` | no | |
| `current_lng` | `float` | no | |
| `battery_percent` | `int` | yes | 0–100 |
| `points_treated_today` | `int` | no | Default `0` |
| `target_waypoint_id` | `str \| None` | no | ObjectId string of the waypoint the robot is currently dispatched to. `None` when idle. Set by the mobile app via `PATCH /api/robot-status/{id}`. |
| `mission_state` | `Literal["idle", "navigating", "inside_boundary", "treating", "completed"]` | no | The robot's current mission phase. Updated by the robot on each heartbeat. Defaults to `"idle"`. |

### Response Schema (`RobotStatusOut`)
All update fields, plus:
| Field | Type | Notes |
|---|---|---|
| `robot_id` | `str` | Path param used as document key |
| `last_sync` | `datetime` | _(server-set)_ UTC upsert time |
| `overall_status` | `str` | _(server-set)_ `"operational"` \| `"low_battery"` \| `"gps_lost"` \| `"degraded"` |
| `target_waypoint_id` | `str \| None` | Passed through. The waypoint the robot is currently navigating to. |
| `mission_state` | `str` | Passed through. The robot's current mission phase. |

## 4. Treatment Events

### Request Schema (`TreatmentEventCreate`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `robot_id` | `str` | yes | |
| `waypoint_id` | `str` | yes | ObjectId string; validated to exist |
| `dosage_ml` | `float` | yes | Volume of flocculant dispensed (mL) |
| `pollution_level` | `Literal["low", "medium", "high"]` | yes | Robot-assessed pollution level |
| `floc_aggregation_time_sec` | `int` | no | Time for floc to form (seconds) |
| `eta_next_area_sec` | `int` | no | Estimated travel time to next waypoint |

### Response Schema (`TreatmentEventOut`)
All create fields, plus:
| Field | Type | Notes |
|---|---|---|
| `id` | `str` | MongoDB `_id` as string |
| `started_at` | `datetime` | _(server-set)_ UTC insert time |
| `ended_at` | `datetime \| None` | Nullable |
| `outcome` | `Literal["collected", "recollection_needed"] \| None` | Nullable |

## 5. AI Chat Logs

### Request Schema (`ChatMessageCreate`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `user_id` | `str` | yes | App user identifier |
| `robot_id` | `str` | yes | Used to build context |
| `message` | `str` | yes | The user's question |

### Response Schema (`ChatMessageOut`)
| Field | Type | Notes |
|---|---|---|
| `id` | `str` | MongoDB `_id` as string |
| `role` | `Literal["user", "assistant"]` | |
| `message` | `str` | The message content |
| `timestamp` | `datetime` | _(server-set)_ UTC |
| `context_snapshot` | `object \| None` | Only on assistant messages |
