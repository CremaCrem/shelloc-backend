from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps robot_id to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, robot_id: str):
        await websocket.accept()
        if robot_id not in self.active_connections:
            self.active_connections[robot_id] = []
        self.active_connections[robot_id].append(websocket)
        logger.info(f"Client connected to robot {robot_id}. Total active: {len(self.active_connections[robot_id])}")

    def disconnect(self, websocket: WebSocket, robot_id: str):
        if robot_id in self.active_connections:
            if websocket in self.active_connections[robot_id]:
                self.active_connections[robot_id].remove(websocket)
                logger.info(f"Client disconnected from robot {robot_id}. Total active: {len(self.active_connections[robot_id])}")
            if not self.active_connections[robot_id]:
                del self.active_connections[robot_id]

    async def broadcast_to_robot(self, robot_id: str, message: dict):
        """Broadcasts a JSON message to all clients subscribed to this robot_id."""
        if robot_id in self.active_connections:
            # Create a copy of the list to iterate safely in case a socket drops
            connections = list(self.active_connections[robot_id])
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to a websocket for robot {robot_id}: {e}")
                    self.disconnect(connection, robot_id)

# Singleton instance
manager = ConnectionManager()
