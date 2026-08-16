import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@patch("app.services.ai_service.genai.Client")
def test_ai_chat_flow(mock_client_class):
    user_id = f"test_user_chat_{uuid.uuid4().hex[:8]}"
    robot_id = f"test_robot_chat_{uuid.uuid4().hex[:8]}"
    
    # Setup mock
    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "**Recommendation:** Mock AI response from Gemini."
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client_instance
    
    # Send message
    chat_resp = client.post("/api/ai-chat/", json={
        "user_id": user_id,
        "robot_id": robot_id,
        "message": "What is the status of my robot?"
    })
    
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["role"] == "assistant"
    assert "mock ai response" in data["message"].lower()
    assert data["context_snapshot"] is not None
    assert data["context_snapshot"]["robot_id"] == robot_id
    
    # Get history
    hist_resp = client.get(f"/api/ai-chat/history?user_id={user_id}")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) == 2 # 1 user msg, 1 assistant msg
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"
