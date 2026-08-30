import os
import time
import math
import random
import httpx
from httpx import HTTPError

API_URL = os.environ.get("API_URL", "http://localhost:8000/api")
API_KEY = os.environ.get("API_KEY", "shelloc0f6yedayyHZwykzIcyLo1hoKAa3GpmAl")
ROBOT_ID = os.environ.get("ROBOT_ID", "SHELLOC-01")
SIM_SPEED_MS = float(os.environ.get("SIM_SPEED_MS", 5.0))
HEARTBEAT_INTERVAL_SEC = 2.0

MAX_RETRIES = 3

# Starting coordinate (somewhere near Manila)
START_LAT = 14.5995
START_LNG = 120.9842

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

client = httpx.Client(timeout=10.0)

def robust_request(method, url, **kwargs):
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
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def compute_step(lat1, lon1, lat2, lon2, step_meters):
    dist = haversine_distance(lat1, lon1, lat2, lon2)
    if dist <= step_meters:
        return lat2, lon2
    ratio = step_meters / dist
    new_lat = lat1 + (lat2 - lat1) * ratio
    new_lon = lon1 + (lon2 - lon1) * ratio
    return new_lat, new_lon

def generate_initial_baseline():
    return {
        "turbidity_ntu": random.uniform(110.33, 146.51),
        "ph": random.uniform(4.95, 6.03), # Often acidic
        "tds_ppm": random.uniform(394.16, 485.13),
    }

def apply_treatment_improvement(current):
    # Turbidity: < 20
    # pH: 6.05 - 6.86
    # TDS: 197.16 - 243.12
    new_ntu = current["turbidity_ntu"] * random.uniform(0.1, 0.4)
    # Flocculant helps turbidity but might not fix pH fully
    ph_diff = 6.46 - current["ph"]
    new_ph = current["ph"] + (ph_diff * random.uniform(0.1, 0.4))
    tds_diff = current["tds_ppm"] - 216.59
    new_tds = current["tds_ppm"] - (tds_diff * random.uniform(0.3, 0.5))
    
    return {
        "turbidity_ntu": max(10.0, new_ntu),
        "ph": min(7.5, max(4.0, new_ph)),
        "tds_ppm": max(150.0, new_tds)
    }

def apply_adaptive_stabilization(current):
    # Citric acid explicitly fixes pH
    ph_diff = 6.46 - current["ph"]
    new_ph = current["ph"] + (ph_diff * random.uniform(0.8, 1.1))
    return {
        "turbidity_ntu": current["turbidity_ntu"],
        "ph": min(6.86, max(6.05, new_ph)),
        "tds_ppm": current["tds_ppm"]
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
    
    current_reading = None
    before_id = None
    after_id = None
    
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
            
        if mission_state == "idle":
            status_resp = robust_request("GET", f"{API_URL}/robot-status/{ROBOT_ID}")
            if status_resp and status_resp.status_code == 200:
                status_data = status_resp.json()
                new_target = status_data.get("target_waypoint_id")
                
                if new_target:
                    print(f"Dispatched to waypoint: {new_target}")
                    wp_resp = robust_request("GET", f"{API_URL}/waypoints/{new_target}")
                    if wp_resp and wp_resp.status_code == 200:
                        wp_data = wp_resp.json()
                        target_wp_id = new_target
                        target_lat = wp_data["latitude"]
                        target_lng = wp_data["longitude"]
                        target_radius = wp_data.get("radius_meters", 2.0)
                        mission_state = "navigating"
                        
        elif mission_state == "navigating":
            dist = haversine_distance(current_lat, current_lng, target_lat, target_lng)
            print(f"Navigating... Distance to target: {dist:.2f}m")
            if dist <= target_radius:
                print(f"Arrived at waypoint {target_wp_id}! Evaluating baseline.")
                mission_state = "baseline_evaluating"
            else:
                current_lat, current_lng = compute_step(current_lat, current_lng, target_lat, target_lng, SIM_SPEED_MS * HEARTBEAT_INTERVAL_SEC)
                time.sleep(HEARTBEAT_INTERVAL_SEC)
                continue
                
        elif mission_state == "baseline_evaluating":
            print("Taking BEFORE reading...")
            current_reading = generate_initial_baseline()
            payload = {
                "robot_id": ROBOT_ID,
                "waypoint_id": target_wp_id,
                "phase": "before",
                **current_reading
            }
            b_resp = robust_request("POST", f"{API_URL}/sensor-readings/", json=payload, headers=HEADERS)
            if b_resp:
                before_id = b_resp.json().get("id")
            print(f"Baseline: NTU {current_reading['turbidity_ntu']:.1f}, pH {current_reading['ph']:.2f}")
            mission_state = "dispensing_flocculant"
            
        elif mission_state == "dispensing_flocculant":
            print("Dispensing Moringa-Chitosan...")
            time.sleep(2)
            event_payload = {
                "robot_id": ROBOT_ID,
                "waypoint_id": target_wp_id,
                "moringa_chitosan_ml": random.uniform(30.0, 60.0),
                "citric_acid_ml": 0.0,
                "pollution_level": "medium",
                "floc_aggregation_time_sec": random.randint(300, 600)
            }
            robust_request("POST", f"{API_URL}/treatment-events/", json=event_payload, headers=HEADERS)
            mission_state = "incubating_15m"
            
        elif mission_state == "incubating_15m":
            print("Incubating for 15 minutes (simulated)...")
            time.sleep(4)
            mission_state = "mesh_biochar_filtering"
            
        elif mission_state == "mesh_biochar_filtering":
            print("Filtering with Mesh & Biochar...")
            time.sleep(3)
            mission_state = "post_evaluating"
            
        elif mission_state == "post_evaluating":
            print("Taking AFTER reading...")
            current_reading = apply_treatment_improvement(current_reading)
            payload = {
                "robot_id": ROBOT_ID,
                "waypoint_id": target_wp_id,
                "phase": "after",
                **current_reading
            }
            a_resp = robust_request("POST", f"{API_URL}/sensor-readings/", json=payload, headers=HEADERS)
            if a_resp:
                after_id = a_resp.json().get("id")
                
            print(f"Post-eval: NTU {current_reading['turbidity_ntu']:.1f}, pH {current_reading['ph']:.2f}")
            
            if is_within_targets(current_reading):
                print("Targets met! Completing...")
                mission_state = "completed"
            else:
                print("Targets not met! Triggering adaptive stabilization...")
                mission_state = "adaptive_stabilization"
                
        elif mission_state == "adaptive_stabilization":
            print("Dispensing Citric Acid for pH adjustment...")
            time.sleep(2)
            event_payload = {
                "robot_id": ROBOT_ID,
                "waypoint_id": target_wp_id,
                "moringa_chitosan_ml": 0.0,
                "citric_acid_ml": random.uniform(10.0, 25.0),
                "pollution_level": "low"
            }
            robust_request("POST", f"{API_URL}/treatment-events/", json=event_payload, headers=HEADERS)
            
            current_reading = apply_adaptive_stabilization(current_reading)
            print("Stabilization complete. Re-evaluating...")
            mission_state = "post_evaluating"
            
        elif mission_state == "completed":
            print(f"Mission complete for {target_wp_id}. Returning to idle.")
            patch_data = {
                "treated": True,
                "before_reading_id": before_id,
                "after_reading_id": after_id,
                "treated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            robust_request("PATCH", f"{API_URL}/waypoints/{target_wp_id}", json=patch_data, headers=HEADERS)
            robust_request("PATCH", f"{API_URL}/robot-status/{ROBOT_ID}", json={"target_waypoint_id": None}, headers=HEADERS)
            
            mission_state = "idle"
            target_wp_id = None
            before_id = None
            after_id = None
            current_reading = None
            
        time.sleep(HEARTBEAT_INTERVAL_SEC)

if __name__ == "__main__":
    main()
