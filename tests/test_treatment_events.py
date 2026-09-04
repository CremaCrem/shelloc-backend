import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)
VALID_API_KEY = settings.API_KEY

def test_treatment_event_flow():
    robot_id = f"test_robot_events_{uuid.uuid4().hex[:8]}"
    # 1. Create waypoint
    wp_resp = client.post("/api/waypoints/", json={
        "robot_id": robot_id,
        "point_number": 1,
        "latitude": 10.0,
        "longitude": 20.0
    })
    wp_id = wp_resp.json()["id"]
    
    # 2. Create treatment event
    evt_resp = client.post("/api/treatment-events/", headers={"X-API-Key": VALID_API_KEY}, json={
        "robot_id": robot_id,
        "waypoint_id": wp_id,
        "moringa_chitosan_ml": 500.0,
        "citric_acid_ml": 50.0,
        "pollution_level": "medium",
        "floc_aggregation_time_sec": 300,
        "eta_next_area_sec": 120
    })
    assert evt_resp.status_code == 201
    data = evt_resp.json()
    assert data["started_at"] is not None
    assert data["ended_at"] is None
    evt_id = data["id"]
    
    # 3. List
    list_resp = client.get(f"/api/treatment-events/?robot_id={robot_id}")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    
    # 4. Get single
    get_resp = client.get(f"/api/treatment-events/{evt_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["moringa_chitosan_ml"] == 500.0

def test_treatment_event_invalid_waypoint():
    robot_id = f"test_robot_events_{uuid.uuid4().hex[:8]}"
    bad_evt = client.post("/api/treatment-events/", headers={"X-API-Key": VALID_API_KEY}, json={
        "robot_id": robot_id,
        "waypoint_id": "5f8f8c44b54764421b7156c3",
        "moringa_chitosan_ml": 500.0,
        "citric_acid_ml": 50.0,
        "pollution_level": "medium"
    })
    assert bad_evt.status_code == 404
