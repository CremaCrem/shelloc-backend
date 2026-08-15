import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)
VALID_API_KEY = settings.API_KEY

def test_sensor_reading_flow():
    robot_id = f"test_robot_sensors_{uuid.uuid4().hex[:8]}"
    # 1. Create waypoint
    wp_resp = client.post("/api/waypoints/", json={
        "robot_id": robot_id,
        "point_number": 1,
        "latitude": 10.0,
        "longitude": 20.0
    })
    wp_id = wp_resp.json()["id"]
    
    # 2. Test status computation (good)
    sr_good = client.post("/api/sensor-readings/", headers={"X-API-Key": VALID_API_KEY}, json={
        "robot_id": robot_id,
        "waypoint_id": wp_id,
        "phase": "after",
        "turbidity_ntu": 15.0,
        "ph": 7.0,
        "tds_ppm": 200.0
    })
    assert sr_good.status_code == 201
    assert sr_good.json()["status"] == "good"
    
    # 3. Test status computation (critical)
    sr_crit = client.post("/api/sensor-readings/", headers={"X-API-Key": VALID_API_KEY}, json={
        "robot_id": robot_id,
        "waypoint_id": wp_id,
        "phase": "before",
        "turbidity_ntu": 60.0,
        "ph": 7.0,
        "tds_ppm": 200.0
    })
    assert sr_crit.status_code == 201
    assert sr_crit.json()["status"] == "critical"
    
    # 4. Get latest
    latest_resp = client.get(f"/api/sensor-readings/latest?robot_id={robot_id}")
    assert latest_resp.status_code == 200
    # Should only return the most recent one for the waypoint, which was sr_crit
    assert len(latest_resp.json()) == 1
    assert latest_resp.json()[0]["id"] == sr_crit.json()["id"]

def test_sensor_reading_invalid_waypoint():
    robot_id = f"test_robot_sensors_{uuid.uuid4().hex[:8]}"
    bad_wp = client.post("/api/sensor-readings/", headers={"X-API-Key": VALID_API_KEY}, json={
        "robot_id": robot_id,
        "waypoint_id": "5f8f8c44b54764421b7156c3", # fake valid objectid
        "phase": "before",
        "turbidity_ntu": 15.0,
        "ph": 7.0,
        "tds_ppm": 200.0
    })
    assert bad_wp.status_code == 404
