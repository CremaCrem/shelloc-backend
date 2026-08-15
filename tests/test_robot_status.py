import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

# We use the configured API key for valid requests
VALID_API_KEY = settings.API_KEY
INVALID_API_KEY = "wrong-key-123"

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["app_status"] == "ok"

def test_robot_status_no_api_key():
    robot_id = f"robot_{uuid.uuid4().hex[:8]}"
    response = client.post(f"/api/robot-status/{robot_id}", json={
        "operation_mode": "autonomous",
        "battery_percent": 100
    })
    assert response.status_code == 401

def test_robot_status_wrong_api_key():
    robot_id = f"robot_{uuid.uuid4().hex[:8]}"
    response = client.post(f"/api/robot-status/{robot_id}", headers={"X-API-Key": INVALID_API_KEY}, json={
        "operation_mode": "autonomous",
        "battery_percent": 100
    })
    assert response.status_code == 401

def test_robot_status_invalid_body():
    robot_id = f"robot_{uuid.uuid4().hex[:8]}"
    # missing battery_percent
    response = client.post(f"/api/robot-status/{robot_id}", headers={"X-API-Key": VALID_API_KEY}, json={
        "operation_mode": "autonomous"
    })
    assert response.status_code == 422

def test_robot_status_valid_request():
    robot_id = f"robot_{uuid.uuid4().hex[:8]}"
    payload = {
        "operation_mode": "autonomous",
        "gps_signal": "good",
        "current_lat": 12.34,
        "current_lng": 56.78,
        "battery_percent": 85,
        "points_treated_today": 2
    }
    # First valid request
    response = client.post(f"/api/robot-status/{robot_id}", headers={"X-API-Key": VALID_API_KEY}, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["robot_id"] == robot_id
    assert data["overall_status"] == "operational"
    assert "last_sync" in data
    
    # Verify we can GET it
    get_response = client.get(f"/api/robot-status/{robot_id}")
    assert get_response.status_code == 200
    assert get_response.json()["overall_status"] == "operational"

def test_robot_status_upsert_update():
    robot_id = f"robot_{uuid.uuid4().hex[:8]}"
    payload = {
        "operation_mode": "manual",
        "gps_signal": "none",
        "battery_percent": 15,
        "points_treated_today": 2
    }
    # Second valid request for the same robot (creates it here)
    response = client.post(f"/api/robot-status/{robot_id}", headers={"X-API-Key": VALID_API_KEY}, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "degraded" # <20 batt + none gps

def test_robot_status_dispatch():
    robot_id = f"robot_{uuid.uuid4().hex[:8]}"
    # 1. Create a waypoint to dispatch to
    wp_response = client.post("/api/waypoints/", json={
        "robot_id": robot_id,
        "point_number": 1,
        "latitude": 10.0,
        "longitude": 20.0
    })
    assert wp_response.status_code == 201
    wp_id = wp_response.json()["id"]

    # 2. Set robot status to idle (using POST heartbeat)
    client.post(f"/api/robot-status/{robot_id}", headers={"X-API-Key": VALID_API_KEY}, json={
        "operation_mode": "autonomous",
        "battery_percent": 100,
        "mission_state": "idle"
    })

    # 3. Dispatch to waypoint
    dispatch_resp = client.patch(f"/api/robot-status/{robot_id}", json={
        "target_waypoint_id": wp_id
    })
    assert dispatch_resp.status_code == 200
    assert dispatch_resp.json()["target_waypoint_id"] == wp_id
    assert dispatch_resp.json()["mission_state"] == "idle" # Patch doesn't change state

    # 4. Robot heartbeats that it's navigating
    client.post(f"/api/robot-status/{robot_id}", headers={"X-API-Key": VALID_API_KEY}, json={
        "operation_mode": "autonomous",
        "battery_percent": 100,
        "mission_state": "navigating"
    })

    # 5. Try dispatching again while navigating (should fail)
    wp2_response = client.post("/api/waypoints/", json={
        "robot_id": robot_id,
        "point_number": 2,
        "latitude": 11.0,
        "longitude": 21.0
    })
    wp2_id = wp2_response.json()["id"]

    bad_dispatch = client.patch(f"/api/robot-status/{robot_id}", json={
        "target_waypoint_id": wp2_id
    })
    assert bad_dispatch.status_code == 400
    
    # 6. Cancel target
    cancel_resp = client.patch(f"/api/robot-status/{robot_id}", json={
        "target_waypoint_id": None
    })
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["target_waypoint_id"] is None
    assert cancel_resp.json()["mission_state"] == "idle"
