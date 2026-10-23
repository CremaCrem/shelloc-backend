"""The robot firmware is built separately; the server should accept what it is likely to send."""
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)
HEADERS = {"X-API-Key": settings.API_KEY}


def rid():
    return f"test_compat_{uuid.uuid4().hex[:8]}"


def test_heartbeat_with_firmware_doc_field_names():
    # Exactly the example payload from docs/firmware-requirements.md (old version)
    robot_id = rid()
    resp = client.post(f"/api/robot-status/{robot_id}", headers=HEADERS, json={
        "battery_percent": 86.5,
        "gps_lat": 1.290270,
        "gps_lng": 103.851959,
        "heading_degrees": 135.5,
        "status": "navigating",
    })
    assert resp.status_code == 200, resp.text
    doc = client.get(f"/api/robot-status/{robot_id}").json()
    assert doc["current_lat"] == 1.290270
    assert doc["current_lng"] == 103.851959
    assert doc["mission_state"] == "navigating"
    assert doc["battery_percent"] == 86.5


def test_heartbeat_tolerates_odd_values_and_keeps_unsent_fields():
    robot_id = rid()
    client.post(f"/api/robot-status/{robot_id}", headers=HEADERS, json={
        "operation_mode": "autonomous", "battery_percent": 15, "gps_signal": "good",
        "flocculant_tank_percent": 70, "biochar_health_status": "degraded",
    })
    # Partial heartbeat: battery omitted, heading out of range, battery overshoot elsewhere
    resp = client.post(f"/api/robot-status/{robot_id}", headers=HEADERS, json={"heading_degrees": -90})
    assert resp.status_code == 200, resp.text
    doc = resp.json()
    assert doc["heading_degrees"] == 270
    assert doc["battery_percent"] == 15          # kept from the earlier heartbeat
    assert doc["overall_status"] == "low_battery"  # judged on stored battery, not "missing"
    assert doc["flocculant_tank_percent"] == 70
    assert doc["biochar_health_status"] == "degraded"

    resp = client.post(f"/api/robot-status/{robot_id}", headers=HEADERS, json={"battery_percent": 101})
    assert resp.status_code == 200
    assert resp.json()["battery_percent"] == 100


def test_buoyancy_failsafe_overall_status():
    robot_id = rid()
    resp = client.post(f"/api/robot-status/{robot_id}", headers=HEADERS, json={
        "battery_percent": 90, "gps_signal": "none", "buoyancy_failsafe_active": True,
        "mission_state": "failsafe_buoyancy",
    })
    assert resp.json()["overall_status"] == "buoyancy_failsafe"


def test_live_reading_with_temperature_and_short_names():
    robot_id = rid()
    resp = client.post("/api/sensor-readings/", headers=HEADERS, json={
        "robot_id": robot_id, "turbidity": 35.0, "ph": 6.8, "tds": 300.0, "temperature": 28.4,
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["waypoint_id"] is None and body["phase"] is None
    assert body["turbidity_ntu"] == 35.0 and body["tds_ppm"] == 300.0
    assert body["temperature_celsius"] == 28.4
    assert body["status"] == "borderline"

    # A reading with a missing sensor is still stored
    resp = client.post("/api/sensor-readings/", headers=HEADERS, json={"robot_id": robot_id, "tds_ppm": 250.0})
    assert resp.status_code == 201
    assert resp.json()["status"] == "no_data"

    newest = client.get(f"/api/sensor-readings/?robot_id={robot_id}&limit=1").json()
    assert newest[0]["tds_ppm"] == 250.0


def test_before_after_readings_link_to_waypoint_automatically():
    robot_id = rid()
    wp_id = client.post("/api/waypoints/", json={
        "robot_id": robot_id, "point_number": 1, "latitude": 14.0, "longitude": 120.0,
    }).json()["id"]

    before = client.post("/api/sensor-readings/", headers=HEADERS, json={
        "robot_id": robot_id, "waypoint_id": wp_id, "phase": "before",
        "turbidity_ntu": 120.0, "ph": 5.5, "tds_ppm": 450.0, "temperature_celsius": 29.0,
    }).json()
    after = client.post("/api/sensor-readings/", headers=HEADERS, json={
        "robot_id": robot_id, "waypoint_id": wp_id, "phase": "after",
        "turbidity_ntu": 15.0, "ph": 6.5, "tds_ppm": 220.0, "temperature_celsius": 28.8,
    }).json()

    # The list the app loads now carries the readings inline
    wps = client.get(f"/api/waypoints/robot/{robot_id}").json()
    assert len(wps) == 1
    wp = wps[0]
    assert wp["treated"] is True and wp["treated_at"]
    assert wp["before_reading"]["id"] == before["id"]
    assert wp["after_reading"]["id"] == after["id"]
    assert wp["after_reading"]["temperature_celsius"] == 28.8
