import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_websocket_robot_status_broadcast():
    """
    Test that a connected websocket receives broadcasts when the robot status is updated.
    """
    robot_id = "test-ws-robot-01"
    headers = {"X-API-Key": settings.API_KEY}
    
    # Establish WebSocket connection
    with client.websocket_connect(f"/ws/robot/{robot_id}") as websocket:
        # In another thread/call (simulated here by a direct REST call), update the robot status
        payload = {
            "operation_mode": "autonomous",
            "battery_percent": 90,
            "gps_signal": "good",
            "current_lat": 14.0,
            "current_lng": 120.0,
            "mission_state": "navigating"
        }
        
        # Trigger the status update via HTTP POST
        response = client.post(f"/api/robot-status/{robot_id}", json=payload, headers=headers)
        assert response.status_code == 200
        
        # Now read from the websocket to see if the broadcast arrived
        data = websocket.receive_json()
        
        # Assert the broadcasted data matches what we expect
        assert data["robot_id"] == robot_id
        assert data["mission_state"] == "navigating"
        assert data["battery_percent"] == 90
        assert data["overall_status"] == "operational"

def test_websocket_disconnect():
    """
    Test that disconnecting a websocket works without erroring.
    """
    robot_id = "test-ws-robot-02"
    with client.websocket_connect(f"/ws/robot/{robot_id}") as websocket:
        # Just connecting and then leaving the context manager closes the connection
        pass
        
    # Test passed if it doesn't raise any errors on close.
