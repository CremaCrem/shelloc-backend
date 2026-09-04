import pytest
import threading
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

from pymongo import MongoClient



@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def receive_with_timeout(ws, timeout=1.0):
    result = []
    def target():
        try:
            result.append(ws.receive_json())
        except Exception as e:
            print(f"[TEST DEBUG] Thread caught exception: {type(e).__name__} - {e}")
    t = threading.Thread(target=target)
    t.start()
    t.join(timeout)
    if t.is_alive():
        print(f"[TEST DEBUG] Thread timed out after {timeout}s!")
        return None
    if not result:
        print("[TEST DEBUG] Thread finished but result is empty!")
    return result[0] if result else None

def test_manual_control_relay(client):
    robot_id = "test-ws-manual-01"
    # Connect edge and two mobiles to verify routing
    with client.websocket_connect(f"/ws/robot/{robot_id}?role=edge") as edge_ws:
        with client.websocket_connect(f"/ws/robot/{robot_id}?role=mobile") as mobile_ws1:
            with client.websocket_connect(f"/ws/robot/{robot_id}?role=mobile") as mobile_ws2:
                payload = {
                    "event": "manual_control",
                    "data": {"x": 0.5, "y": -0.5}
                }
                mobile_ws1.send_json(payload)
                
                # Edge should receive it
                data = receive_with_timeout(edge_ws, timeout=5.0)
                assert data["event"] == "manual_control"
                assert data["data"]["x"] == 0.5
                
                # Negative assertion: mobile_ws2 should NOT receive the manual_control
                # We use a short timeout receive so we don't rely on unrelated broadcast behavior
                data2 = receive_with_timeout(mobile_ws2, timeout=1.0)
                assert data2 is None, "Mobile 2 should not receive the manual_control broadcast"

def test_invalid_joystick_payload_rejected(client):
    robot_id = "test-ws-manual-02"
    with client.websocket_connect(f"/ws/robot/{robot_id}?role=edge") as edge_ws:
        with client.websocket_connect(f"/ws/robot/{robot_id}?role=mobile") as mobile_ws:
            # Out of bounds x
            payload = {
                "event": "manual_control",
                "data": {"x": 2.0, "y": 0.0}
            }
            mobile_ws.send_json(payload)
            
            # Send a valid one immediately after
            valid_payload = {
                "event": "manual_control",
                "data": {"x": 1.0, "y": 0.0}
            }
            mobile_ws.send_json(valid_payload)
            
            data = edge_ws.receive_json()
            assert data["event"] == "manual_control"
            # It should be the second valid payload, meaning the first was dropped
            assert data["data"]["x"] == 1.0

def test_resume_autonomous_with_active_waypoint(client):
    robot_id = "test-ws-manual-03b"
    headers = {"X-API-Key": settings.API_KEY}
    
    # 1. Create a real waypoint to get a valid ObjectId
    wp_payload = {
        "robot_id": robot_id,
        "point_number": 1,
        "latitude": 14.1,
        "longitude": 120.1
    }
    wp_resp = client.post("/api/waypoints/", json=wp_payload, headers=headers)
    assert wp_resp.status_code == 201
    real_wp_id = wp_resp.json()["id"]
    
    # 2. Setup initial state and dispatch to waypoint
    payload = {
        "operation_mode": "autonomous",
        "battery_percent": 90,
        "gps_signal": "good",
        "current_lat": 14.0,
        "current_lng": 120.0,
        "mission_state": "idle"
    }
    client.post(f"/api/robot-status/{robot_id}", json=payload, headers=headers)
    
    # 3. Dispatch robot using the real ObjectId
    client.patch(f"/api/robot-status/{robot_id}", json={"target_waypoint_id": real_wp_id}, headers=headers)
    
    # 4. Force state to manual_override so resume_autonomous is accepted
    override_payload = payload.copy()
    override_payload["mission_state"] = "manual_override"
    client.post(f"/api/robot-status/{robot_id}", json=override_payload, headers=headers)
    
    with client.websocket_connect(f"/ws/robot/{robot_id}?role=edge") as edge_ws:
        with client.websocket_connect(f"/ws/robot/{robot_id}?role=mobile") as mobile_ws:
            mobile_ws.send_json({"event": "resume_autonomous"})
            
            # Edge should receive the resume_navigation command with the waypoint_id
            # Wait for this FIRST to synchronize with the server processing
            data = receive_with_timeout(edge_ws, timeout=5.0)
            assert data.get("event") == "resume_navigation"
            assert data.get("waypoint_id") == real_wp_id

            response = client.get(f"/api/robot-status/{robot_id}")
            assert response.json()["mission_state"] == "navigating"

def test_resume_autonomous_without_active_waypoint(client):
    robot_id = "test-ws-manual-04"
    headers = {"X-API-Key": settings.API_KEY}
    
    payload = {
        "operation_mode": "autonomous",
        "battery_percent": 90,
        "gps_signal": "good",
        "current_lat": 14.0,
        "current_lng": 120.0,
        "mission_state": "manual_override",
        "target_waypoint_id": None
    }
    client.post(f"/api/robot-status/{robot_id}", json=payload, headers=headers)
    
    with client.websocket_connect(f"/ws/robot/{robot_id}?role=edge") as edge_ws:
        with client.websocket_connect(f"/ws/robot/{robot_id}?role=mobile") as mobile_ws:
            mobile_ws.send_json({"event": "resume_autonomous"})
            
            # Edge should NOT receive a resume_navigation command since there is no active waypoint
            # We do this FIRST so it actually executes before the state assertion can short-circuit
            data = receive_with_timeout(edge_ws, timeout=1.0)
            assert data is None, "Edge should not receive resume_navigation command when no waypoint exists"
            
            response = client.get(f"/api/robot-status/{robot_id}")
            assert response.json()["mission_state"] == "idle"

def test_malformed_messages_dont_crash(client):
    robot_id = "test-ws-manual-05"
    with client.websocket_connect(f"/ws/robot/{robot_id}?role=edge") as edge_ws:
        with client.websocket_connect(f"/ws/robot/{robot_id}?role=mobile") as mobile_ws:
            # Send completely malformed text
            mobile_ws.send_text("NOT JSON")
            # Send JSON with missing fields
            mobile_ws.send_json({"foo": "bar"})
            
            # Send valid message to ensure socket is alive and processes it
            valid_payload = {"event": "manual_control", "data": {"x": 0.0, "y": 0.0}}
            mobile_ws.send_json(valid_payload)
            
            data = edge_ws.receive_json()
            assert data["event"] == "manual_control"


def test_resume_autonomous_wrong_state_ignored(client):
    robot_id = "test-ws-manual-06"
    headers = {"X-API-Key": settings.API_KEY}
    
    # Setup initial state as navigating
    payload = {
        "operation_mode": "autonomous",
        "battery_percent": 90,
        "gps_signal": "good",
        "current_lat": 14.0,
        "current_lng": 120.0,
        "mission_state": "navigating",
        "target_waypoint_id": None
    }
    client.post(f"/api/robot-status/{robot_id}", json=payload, headers=headers)
    
    with client.websocket_connect(f"/ws/robot/{robot_id}?role=edge") as edge_ws:
        with client.websocket_connect(f"/ws/robot/{robot_id}?role=mobile") as mobile_ws:
            mobile_ws.send_json({"event": "resume_autonomous"})
            
            # Edge should NOT receive a resume_navigation command because state isn't manual_override
            data = receive_with_timeout(edge_ws, timeout=1.0)
            assert data is None, "Edge should not receive resume_navigation command when not in manual_override"
            
            response = client.get(f"/api/robot-status/{robot_id}")
            assert response.json()["mission_state"] == "navigating"

def test_telemetry_broadcast_includes_heading_degrees(client):
    robot_id = "test-ws-manual-07"
    headers = {"X-API-Key": settings.API_KEY}
    
    # 1. Connect a mobile client to listen for telemetry
    with client.websocket_connect(f"/ws/robot/{robot_id}?role=mobile") as mobile_ws:
        
        # 2. Edge node posts status update with heading_degrees
        payload = {
            "operation_mode": "autonomous",
            "battery_percent": 85,
            "gps_signal": "good",
            "current_lat": 14.0,
            "current_lng": 120.0,
            "heading_degrees": 275.5,
            "mission_state": "navigating"
        }
        resp = client.post(f"/api/robot-status/{robot_id}", json=payload, headers=headers)
        assert resp.status_code == 200
        
        # 3. Mobile should receive the telemetry broadcast with heading_degrees
        data = receive_with_timeout(mobile_ws, timeout=2.0)
        assert data is not None, "Mobile should receive telemetry broadcast"
        assert data.get("event") == "telemetry"
        assert data.get("data", {}).get("heading_degrees") == 275.5

