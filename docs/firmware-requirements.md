# SHELLOC Firmware Integration Requirements

This document outlines the firmware requirements for the edge device to support real-time map telemetry (heading) and remote manual override, as introduced in mobile app Phases 4 and 5.

## 1. Heading Reporting (IMU/Compass)
To accurately display the robot's orientation on the mobile map, the edge device must report its current heading in degrees (0-359, where 0 is true North).

**Requirement:**
- The edge script must read IMU/magnetometer data and calculate the absolute heading.
- The calculated heading must be appended to the regular telemetry POST payload to `/api/robot-status/{id}` as a float or integer field: `"heading_degrees"`.
- This data should be sent continuously (e.g., every 1-2 seconds) while the robot is active.

**Example Payload:**
```json
{
  "battery_percent": 86.5,
  "gps_lat": 1.290270,
  "gps_lng": 103.851959,
  "heading_degrees": 135.5,
  "status": "navigating"
}
```

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
- The system must re-evaluate its current GPS coordinate, reload the active `target_waypoint_id` (if applicable), and restart the autonomous navigation loop safely.
