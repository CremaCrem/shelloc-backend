import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ai_chat_flow():
    user_id = f"test_user_chat_{uuid.uuid4().hex[:8]}"
    robot_id = f"test_robot_chat_{uuid.uuid4().hex[:8]}"
    
    # Send message
    chat_resp = client.post("/api/ai-chat/", json={
        "user_id": user_id,
        "robot_id": robot_id,
        "message": "What is the status of my robot?"
    })
    
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["role"] == "assistant"
    assert "mocked response" in data["message"].lower() or "mock ai response" in data["message"].lower()
    assert data["context_snapshot"] is not None
    assert data["context_snapshot"]["robot_id"] == robot_id
    
    # Get history
    hist_resp = client.get(f"/api/ai-chat/history?user_id={user_id}")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) == 2 # 1 user msg, 1 assistant msg
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"
