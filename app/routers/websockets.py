from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.connection_manager import manager

router = APIRouter()

@router.websocket("/ws/robot/{robot_id}")
async def websocket_endpoint(websocket: WebSocket, robot_id: str):
    """
    Establish a WebSocket connection to stream live telemetry for a specific robot.
    """
    await manager.connect(websocket, robot_id)
    try:
        # Keep the connection alive
        while True:
            # We don't currently process incoming messages from the mobile client,
            # but we need to receive to keep the socket open and detect disconnects.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, robot_id)
