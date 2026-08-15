import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_create_waypoint_and_max_limit():
    robot_id = f"test_robot_wp_limit_{uuid.uuid4().hex[:8]}"
    
    # Create 6 waypoints
    for i in range(1, 7):
        resp = client.post("/api/waypoints/", json={
            "robot_id": robot_id,
            "point_number": i,
            "latitude": 10.0 + i,
            "longitude": 20.0 + i
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["radius_meters"] == 2.0
        assert data["treated"] is False
    
    # 7th should fail due to DB max count limit
    resp7 = client.post("/api/waypoints/", json={
        "robot_id": robot_id,
        "point_number": 6,  # Valid according to schema, but hits max limit in db
        "latitude": 17.0,
        "longitude": 27.0
    })
    assert resp7.status_code == 400

def test_list_and_get_waypoint():
    robot_id = f"test_robot_wp_list_{uuid.uuid4().hex[:8]}"
    
    # Create 1
    create_resp = client.post("/api/waypoints/", json={
        "robot_id": robot_id,
        "point_number": 1,
        "latitude": 10.0,
        "longitude": 20.0,
        "label": "Custom Label"
    })
    assert create_resp.status_code == 201
    wp_id = create_resp.json()["id"]
    
    # List
    list_resp = client.get(f"/api/waypoints/?robot_id={robot_id}")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["label"] == "Custom Label"
    
    # Get detail
    get_resp = client.get(f"/api/waypoints/{wp_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == wp_id
    assert data["before_reading"] is None
    assert data["after_reading"] is None

def test_update_and_delete_waypoint():
    robot_id = f"test_robot_wp_upd_{uuid.uuid4().hex[:8]}"
    
    create_resp = client.post("/api/waypoints/", json={
        "robot_id": robot_id,
        "point_number": 1,
        "latitude": 10.0,
        "longitude": 20.0
    })
    wp_id = create_resp.json()["id"]
    
    # Update treated
    patch_resp = client.patch(f"/api/waypoints/{wp_id}", json={
        "treated": True
    })
    assert patch_resp.status_code == 200
    assert patch_resp.json()["treated"] is True
    
    # Delete
    del_resp = client.delete(f"/api/waypoints/{wp_id}")
    assert del_resp.status_code == 204
    
    # Get should 404
    get_resp = client.get(f"/api/waypoints/{wp_id}")
    assert get_resp.status_code == 404
