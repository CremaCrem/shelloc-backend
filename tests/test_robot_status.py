import pytest
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
    response = client.post("/api/robot-status/robot_1", json={
        "operation_mode": "autonomous",
        "battery_percent": 100
    })
    assert response.status_code == 401

def test_robot_status_wrong_api_key():
    response = client.post("/api/robot-status/robot_1", headers={"X-API-Key": INVALID_API_KEY}, json={
        "operation_mode": "autonomous",
        "battery_percent": 100
    })
    assert response.status_code == 401

def test_robot_status_invalid_body():
    # missing battery_percent
    response = client.post("/api/robot-status/robot_1", headers={"X-API-Key": VALID_API_KEY}, json={
        "operation_mode": "autonomous"
    })
    assert response.status_code == 422

def test_robot_status_valid_request():
    payload = {
        "operation_mode": "autonomous",
        "gps_signal": "good",
        "current_lat": 12.34,
        "current_lng": 56.78,
        "battery_percent": 85,
        "points_treated_today": 2
    }
    # First valid request
    response = client.post("/api/robot-status/robot_1", headers={"X-API-Key": VALID_API_KEY}, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["robot_id"] == "robot_1"
    assert data["overall_status"] == "operational"
    assert "last_sync" in data
    
    # Verify we can GET it
    get_response = client.get("/api/robot-status/robot_1")
    assert get_response.status_code == 200
    assert get_response.json()["overall_status"] == "operational"

def test_robot_status_upsert_update():
    payload = {
        "operation_mode": "manual",
        "gps_signal": "none",
        "battery_percent": 15,
        "points_treated_today": 2
    }
    # Second valid request for the same robot
    response = client.post("/api/robot-status/robot_1", headers={"X-API-Key": VALID_API_KEY}, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "degraded" # <20 batt + none gps
