# Implementation Specification

This document defines HOW the SHELLOC backend behaves internally: validation rules, server-computed fields, state machine transitions, failsafe handling, and Google Gemini integration.

---

## 1. Core Behavior & Infrastructure

### Configuration (`core/config.py`)
- Loads environment variables once via `python-dotenv`.
- Validates essential parameters on startup (`MONGO_URI`, `DB_NAME`, `API_KEY`, `AI_PROVIDER`, `AI_API_KEY`).
- `AI_PROVIDER` must be set to `"gemini"` targeting `gemini-3.7-flash`.

### Database Driver (`core/database.py`)
- Manages a persistent async Motor connection pool.
- Exposes `get_database()`.

### Authentication Boundaries (`core/auth.py`)
- FastAPI dependency `verify_api_key` validates the `X-API-Key` header against `config.API_KEY`.
- Enforced on all robot write endpoints (`POST /api/sensor-readings`, `POST /api/robot-status/{id}`, `POST /api/treatment-events`).
- Returns `401 Unauthorized` on missing or invalid key.

---

## 2. Server-Computed Status Rules

These fields are strictly computed by the server upon document ingestion to maintain integrity.

### A. Sensor Reading `status`
Computed from both `turbidity_ntu` and `ph`:
```python
def compute_sensor_status(turbidity_ntu: float, ph: float) -> str:
    # Critical conditions
    if turbidity_ntu > 50 or ph < 5.5 or ph > 8.5:
        return "critical"
    # Borderline conditions
    elif (20 <= turbidity_ntu <= 50) or (5.5 <= ph < 6.0) or (7.5 < ph <= 8.5):
        return "borderline"
    # Good / Remediated conditions
    else:
        return "good"
```

### B. Robot Status `overall_status`
Computed from battery percentage, GPS lock, and failsafe flags:
- If `buoyancy_failsafe_active == True`: `"buoyancy_failsafe"`
- If `battery_percent < 20` and `gps_signal == "none"`: `"degraded"`
- If `battery_percent < 20`: `"low_battery"`
- If `gps_signal == "none"`: `"gps_lost"`
- Otherwise: `"operational"`

---

## 3. Closed-Loop Mission Lifecycle & State Machine

SHELLOC operates on a 9-state closed-loop operational lifecycle:

```
[idle] 
   └──> [navigating] (App dispatches target_waypoint_id)
           └──> [baseline_evaluating] (Arrival inside 2m geofence)
                   └──> [dispensing_flocculant] (Pollution classified, primary Moringa dosed)
                           └──> [incubating_15m] (Onboard 15-min countdown active)
                                   └──> [mesh_biochar_filtering] (Collection sweep & biochar absorption)
                                           └──> [post_evaluating] (Measure after-treatment telemetry)
                                                   └──> [adaptive_stabilization] (Citric acid if pH > 7.5; secondary floc if NTU > 20)
                                                           └──> [completed] (Waypoint treated, returns to idle)
[Failsafe Track]
[navigating] ──(GPS signal lost)──> [failsafe_buoyancy] ──(Signal restored)──> [navigating]
```

### State-by-State Execution Logic

1. **`idle`**: Robot rests on water. `target_waypoint_id` is null. Ready for dispatch.
2. **`navigating`**: App issues `PATCH /api/robot-status/{id}` with `target_waypoint_id`. The robot begins heading toward target coordinates while polling SONAR for obstacle avoidance.
3. **`baseline_evaluating`**: When distance to target center is $\le 2.0\text{ m}$ (`radius_meters`), robot transitions to `baseline_evaluating`. Captures baseline telemetry and posts `SensorReadingCreate` with `phase: "before"`.
4. **`dispensing_flocculant`**: Evaluates baseline turbidity/SPM:
   - Low: $20\text{–}50\text{ mg/L}$ (or equivalent NTU)
   - Medium: $50\text{–}120\text{ mg/L}$
   - High: $120\text{–}200\text{ mg/L}$  
   Activates the magnetic stirring compartment and 120 mL/min circulation pump to dispense the calculated Moringa-Chitosan volume.
5. **`incubating_15m`**: Robot holds position for **900 seconds** (15 minutes). The countdown runs locally on the Raspberry Pi edge controller. The robot streams `timer_remaining_sec` in its 5-second heartbeat so clients display a live countdown.
6. **`mesh_biochar_filtering`**: Robot executes a localized sweep across the 2m perimeter, capturing aggregated flocs with its collection mesh and circulating water through the biochar filter to absorb residual dissolved organics and metals.
7. **`post_evaluating`**: Robot captures the post-treatment reading suite and posts `SensorReadingCreate` with `phase: "after"`.
8. **`adaptive_stabilization`**: Closed-loop feedback check:
   - If `turbidity_ntu > 20`: Deploys secondary Moringa-Chitosan micro-dose.
   - If `ph > 7.5`: Deploys Citric Acid micro-dose via secondary dispensary pump to neutralize alkalinity toward the target $6.0\text{–}7.0$ pH window.
   - Logged in `TreatmentEventCreate` with `secondary_treatment_applied: True`.
9. **`completed`**: Updates waypoint (`PATCH /api/waypoints/{id}`, `treated: True`, links reading IDs), increments `points_treated_today`, and resets `mission_state` to `"idle"`.

---

## 4. Edge Architecture & Failsafe Handling

### A. Edge-Orchestrated 15-Minute Countdown
- **Resilience:** The 15-minute incubation timer runs directly on the Raspberry Pi edge controller. If cellular connectivity drops during incubation, the timer continues unimpeded.
- **WebSocket Broadcast:** The backend receives `timer_remaining_sec` on each heartbeat and broadcasts the updated payload to connected clients over `/ws/robot/{robot_id}`.

### B. GPS Buoyancy Control Failsafe
- If `gps_signal == "none"` continuously for $> 10\text{ seconds}$ during navigation:
  1. Firmware enters `failsafe_buoyancy` state.
  2. Activates the 120 mL/min ballast pump to evacuate ballast water.
  3. Increased buoyancy elevates the vessel and raises the GPS/cellular antenna mast above water surface waves.
  4. Once satellite lock is reacquired, normal navigation resumes.

---

## 5. Google Gemini AI Engine (`services/ai_service.py`)

- Integrated via `google-genai` SDK targeting model `gemini-3.7-flash`.
- Injects a grounded context snapshot containing:
  - Active robot telemetry, mission state, and remaining timer seconds.
  - Consumable reservoir levels (Moringa-Chitosan %, Citric Acid %, Biochar health).
  - Linked waypoint before/after comparative sensor deltas.
- **Conversational Memory:** Preserves the last 5 turns per `user_id` from `ai_chat_logs`.
- Formats recommendations with bold callouts (`**Recommendation:** ...`).
