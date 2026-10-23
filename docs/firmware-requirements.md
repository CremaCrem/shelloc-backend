# SHELLOC Firmware Integration Requirements

This document outlines the firmware requirements for the edge device to support real-time map telemetry (heading) and remote manual override, as introduced in mobile app Phases 4 and 5.

## 1. Heading Reporting (IMU/Compass)
To accurately display the robot's orientation on the mobile map, the edge device must report its current heading in degrees (0-359, where 0 is true North).

**Requirement:**
- The edge script must read IMU/magnetometer data and calculate the absolute heading.
- The calculated heading must be appended to the regular telemetry POST payload to `/api/robot-status/{id}` as a float or integer field: `"heading_degrees"`.
- This data should be sent continuously (e.g., every 1-2 seconds) while the robot is active.

**Example Payload** (`POST /api/robot-status/{robot_id}`, header `X-API-Key: <key>`):
```json
{
  "operation_mode": "autonomous",
  "mission_state": "navigating",
  "battery_percent": 86.5,
  "gps_signal": "good",
  "current_lat": 1.290270,
  "current_lng": 103.851959,
  "heading_degrees": 135.5
}
```

> Earlier versions of this document used `gps_lat`, `gps_lng` and `status`. The server still
> accepts those names, but new firmware should use the names above.

## 2. WebSocket Telemetry Streaming
To support low-latency manual control, the edge device must maintain a persistent WebSocket connection to the backend.

**Requirement:**
- Connect via WebSocket to: `wss://<api-host>/ws/robot/<robot_id>?role=edge`
- Implement automatic reconnection logic with exponential backoff if the connection drops.
- The connection must be able to asynchronously receive incoming JSON messages while running the main control loop.

## 3. Remote Manual Override Interruption
The backend/mobile app will send a `manual_control` event to interrupt the autonomous navigation loop.

**Requirement:**
- When the WS client receives an event with `"event": "manual_control"`, it must immediately transition the state machine out of `navigating` and into a manual override state.
- The message payload will contain joystick coordinates:
  ```json
  {
    "event": "manual_control",
    "data": {
      "x": 0.8,
      "y": -0.5
    }
  }
  ```
- **Safety Critical:** The autonomous loop (e.g., GPS PID controller) MUST yield. Motor outputs should now exclusively map to the incoming `x` and `y` vectors.
- `y` maps to forward/backward thrust, `x` maps to differential turning (left/right).
- **Failsafe:** If no `manual_control` packet is received within 500ms (network timeout), zero out all motor speeds to prevent runaway.

## 4. Resuming Autonomous Operation
When the user exits manual control on the app, a resume signal is dispatched.

**Requirement:**
- When the WS client receives an event with `"event": "resume_autonomous"`, the state machine should transition back to `navigating` or `idle`.
  The message carries the active waypoint (or `null`): `{"event": "resume_autonomous", "waypoint_id": "<id or null>"}`.
  When a waypoint is active the server also sends `{"event": "resume_navigation", "waypoint_id": "<id>"}` for older firmware;
  handling either one is enough, and handling both must be safe (resuming twice to the same waypoint).
- The system must re-evaluate its current GPS coordinate, reload the active `target_waypoint_id` (if applicable), and restart the autonomous navigation loop safely.


## 5. What the Server Accepts (summary)

All robot writes need the header `X-API-Key: <API_KEY>` (same value as the backend's `API_KEY` setting).
If the server rejects a request, the reason is written to the backend logs (Render → Logs, "Rejected …").

### Heartbeat — `POST /api/robot-status/{robot_id}` (every 2–5 s)
Every field is optional; send what you have. Fields you leave out keep their last value.

| Field | Example | Notes |
|---|---|---|
| `operation_mode` | `"autonomous"` / `"manual"` | |
| `mission_state` | `"navigating"` | one of the 9 lifecycle states, `failsafe_buoyancy`, or `manual_override` (alias: `status`) |
| `battery_percent` | `86.5` | clamped to 0–100 |
| `gps_signal` | `"good"` / `"weak"` / `"none"` | |
| `current_lat`, `current_lng` | `14.6022`, `120.9880` | aliases: `gps_lat`, `gps_lng` |
| `heading_degrees` | `135.5` | wrapped into 0–360 |
| `flocculant_tank_percent`, `citric_acid_tank_percent` | `70` | 0–100 |
| `biochar_health_status` | `"optimal"` / `"degraded"` / `"replace"` | |
| `timer_remaining_sec` | `512` | during `incubating_15m` |
| `buoyancy_failsafe_active` | `true` | |

The app shows the robot as **offline** if no heartbeat arrives for 30 seconds.

### Water readings — `POST /api/sensor-readings/`
`robot_id` is required; everything else is optional.

| Field | Notes |
|---|---|
| `waypoint_id`, `phase` (`"before"` / `"after"`) | Set both at a waypoint. Leave both out for a **live reading** while moving. |
| `turbidity_ntu` (alias `turbidity`) | NTU |
| `ph` | 0–14 |
| `tds_ppm` (alias `tds`) | ppm |
| `temperature_celsius` (aliases `temperature`, `temperature_c`) | °C |
| `obstacle_detected`, `sonar_distance_cm` | SONAR, shown in the app's Diagnostics |
| `latitude`, `longitude` | where the reading was taken |

A `before` reading is linked to its waypoint automatically; an `after` reading also marks the waypoint
treated. PATCHing the waypoint yourself is no longer required (it still works).

### Manual control — `wss://<api-host>/ws/robot/<robot_id>?role=edge`
- Incoming `manual_control` with `data.x` / `data.y` in −1…1 while the joystick is held (repeated about every 200 ms).
- Incoming `resume_autonomous` (and `resume_navigation`) when the operator exits manual mode (see section 4).
- The server marks the robot `manual_override` itself when driving starts; reporting it from the robot is optional.
