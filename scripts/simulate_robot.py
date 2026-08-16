import os
import time
import math
import random
import httpx
from httpx import HTTPError

API_URL = os.environ.get("API_URL", "http://localhost:8000/api")
API_KEY = os.environ.get("API_KEY", "dev_secret_key")
ROBOT_ID = os.environ.get("ROBOT_ID", "sim-robot-01")
SIM_SPEED_MS = float(os.environ.get("SIM_SPEED_MS", 5.0))
HEARTBEAT_INTERVAL_SEC = 2.0

MAX_RETRIES = 5

# Starting coordinate (somewhere near Manila)
START_LAT = 14.5995
START_LNG = 120.9842

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

client = httpx.Client(timeout=10.0)

def robust_request(method, url, **kwargs):
    """Executes an HTTP request with retries for network/5xx errors."""
    for attempt in range(3):
        try:
            resp = client.request(method, url, **kwargs)
            if resp.status_code >= 500:
                print(f"Server error {resp.status_code} on {url}. Retrying...")
            else:
                return resp
        except HTTPError as e:
            print(f"Network error on {url}: {e}. Retrying...")
        time.sleep(2)
    return None

def haversine_distance(lat1, lon1, lat2, lon2):
    """Returns distance in meters between two coordinates."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def compute_step(lat1, lon1, lat2, lon2, step_meters):
    """Calculates new coordinates after moving step_meters towards target."""
    dist = haversine_distance(lat1, lon1, lat2, lon2)
    if dist <= step_meters:
        return lat2, lon2
    ratio = step_meters / dist
    new_lat = lat1 + (lat2 - lat1) * ratio
    new_lon = lon1 + (lon2 - lon1) * ratio
    return new_lat, new_lon

def generate_initial_baseline():
    """Returns a highly degraded reading to start with."""
    return {
        "turbidity_ntu": random.uniform(110.33, 146.51),
        "ph": random.uniform(4.95, 6.03),
        "tds_ppm": random.uniform(394.16, 485.13),
    }

def apply_treatment_improvement(current):
    """Simulates a partial improvement towards the target windows."""
    # Target windows:
    # Turbidity: 10.40 - 16.25 NTU (we need < 20)
    # pH: 6.05 - 6.86
    # TDS: 197.16 - 243.12
    
    # Improve turbidity by 40-70% per pass
    new_ntu = current["turbidity_ntu"] * random.uniform(0.3, 0.6)
    
    # Improve pH towards 6.5 (diff reduced by 30-60%)
    ph_diff = 6.46 - current["ph"]
    new_ph = current["ph"] + (ph_diff * random.uniform(0.3, 0.6))
    
    # Improve TDS towards 220 (diff reduced by 30-50%)
    tds_diff = current["tds_ppm"] - 216.59
    new_tds = current["tds_ppm"] - (tds_diff * random.uniform(0.3, 0.5))
    
    return {
        "turbidity_ntu": max(10.0, new_ntu),
        "ph": min(7.5, max(4.0, new_ph)),
        "tds_ppm": max(150.0, new_tds)
    }

def is_within_targets(reading):
    ntu_ok = reading["turbidity_ntu"] < 20.0
    ph_ok = 6.05 <= reading["ph"] <= 6.86
    tds_ok = 197.16 <= reading["tds_ppm"] <= 243.12
    return ntu_ok and ph_ok and tds_ok

def main():
    print(f"Starting Simulator for {ROBOT_ID}. API URL: {API_URL}")
    current_lat = START_LAT
    current_lng = START_LNG
    mission_state = "idle"
    target_wp_id = None
    target_lat = None
    target_lng = None
    target_radius = 2.0
    
    while True:
        # 1. Update Robot Status
        payload = {
            "operation_mode": "autonomous",
            "gps_signal": "good",
            "current_lat": current_lat,
            "current_lng": current_lng,
            "battery_percent": 85,
            "mission_state": mission_state
        }
        resp = robust_request("POST", f"{API_URL}/robot-status/{ROBOT_ID}", json=payload, headers=HEADERS)
        if resp is None:
            print("Failed to heartbeat. Sleeping...")
            time.sleep(HEARTBEAT_INTERVAL_SEC)
            continue
            
        # 2. Poll for dispatch
        status_resp = robust_request("GET", f"{API_URL}/robot-status/{ROBOT_ID}")
        if status_resp and status_resp.status_code == 200:
            status_data = status_resp.json()
            new_target = status_data.get("target_waypoint_id")
            
            if mission_state == "idle" and new_target:
                print(f"Dispatched to waypoint: {new_target}")
                wp_resp = robust_request("GET", f"{API_URL}/waypoints/{new_target}")
                if wp_resp and wp_resp.status_code == 200:
                    wp_data = wp_resp.json()
                    target_wp_id = new_target
                    target_lat = wp_data["latitude"]
                    target_lng = wp_data["longitude"]
                    target_radius = wp_data.get("radius_meters", 2.0)
                    mission_state = "navigating"
                    
        # 3. Handle Navigation
        if mission_state == "navigating" and target_lat and target_lng:
            dist = haversine_distance(current_lat, current_lng, target_lat, target_lng)
            print(f"Navigating... Distance to target: {dist:.2f}m")
            
            if dist <= target_radius:
                print(f"Arrived at waypoint {target_wp_id}! Entering boundary.")
                mission_state = "inside_boundary"
            else:
                current_lat, current_lng = compute_step(current_lat, current_lng, target_lat, target_lng, SIM_SPEED_MS * HEARTBEAT_INTERVAL_SEC)
                time.sleep(HEARTBEAT_INTERVAL_SEC)
                continue
                
        # 4. Handle Treatment (inside boundary)
        if mission_state == "inside_boundary":
            mission_state = "treating"
            
            print("Starting Treatment Iteration Loop...")
            current_reading = generate_initial_baseline()
            
            success = False
            for attempt in range(1, MAX_RETRIES + 1):
                print(f"--- Cycle {attempt} ---")
                
                # Take BEFORE reading
                before_payload = {
                    "robot_id": ROBOT_ID,
                    "waypoint_id": target_wp_id,
                    "phase": "before",
                    **current_reading
                }
                b_resp = robust_request("POST", f"{API_URL}/sensor-readings/", json=before_payload, headers=HEADERS)
                if not b_resp:
                    print("Failed to post before reading. Retrying loop.")
                    continue
                before_id = b_resp.json().get("id")
                
                print(f"Dispensing Moringa-Chitosan... waiting for aggregation (simulated).")
                time.sleep(4)  # Simulate wait
                
                # Take AFTER reading (partial improvement)
                current_reading = apply_treatment_improvement(current_reading)
                after_payload = {
                    "robot_id": ROBOT_ID,
                    "waypoint_id": target_wp_id,
                    "phase": "after",
                    **current_reading
                }
                a_resp = robust_request("POST", f"{API_URL}/sensor-readings/", json=after_payload, headers=HEADERS)
                after_id = a_resp.json().get("id") if a_resp else None
                
                # Log Treatment Event
                event_payload = {
                    "robot_id": ROBOT_ID,
                    "waypoint_id": target_wp_id,
                    "dosage_ml": random.uniform(30.0, 60.0),
                    "pollution_level": "high" if attempt == 1 else "medium",
                    "floc_aggregation_time_sec": random.randint(300, 600)
                }
                robust_request("POST", f"{API_URL}/treatment-events/", json=event_payload, headers=HEADERS)
                
                print(f"After values -> NTU: {current_reading['turbidity_ntu']:.1f}, pH: {current_reading['ph']:.2f}, TDS: {current_reading['tds_ppm']:.1f}")
                
                if is_within_targets(current_reading):
                    print("Water is within target remediated windows!")
                    # Mark Waypoint as treated
                    patch_data = {
                        "treated": True,
                        "before_reading_id": before_id,
                        "after_reading_id": after_id,
                        "treated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                    robust_request("PATCH", f"{API_URL}/waypoints/{target_wp_id}", json=patch_data, headers=HEADERS)
                    success = True
                    break
                else:
                    print("Targets not met. Initiating re-treatment...")
                    
            if not success:
                print(f"Reached max retries ({MAX_RETRIES}) without hitting all targets. Giving up on this waypoint.")
                
            mission_state = "completed"
            
        # 5. Handle Completed
        if mission_state == "completed":
            print(f"Mission complete for {target_wp_id}. Returning to idle.")
            # Clear dispatch state on backend by patching null
            robust_request("PATCH", f"{API_URL}/robot-status/{ROBOT_ID}", json={"target_waypoint_id": None}, headers=HEADERS)
            mission_state = "idle"
            target_wp_id = None
            
        time.sleep(HEARTBEAT_INTERVAL_SEC)

if __name__ == "__main__":
    # Ensure directory structure allows direct execution
    main()
