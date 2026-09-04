from typing import Dict, List, Tuple
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps robot_id to a list of (websocket, role) tuples
        self.active_connections: Dict[str, List[Tuple[WebSocket, str]]] = {}

    async def connect(self, websocket: WebSocket, robot_id: str, role: str = "mobile"):
        await websocket.accept()
        if robot_id not in self.active_connections:
            self.active_connections[robot_id] = []
        self.active_connections[robot_id].append((websocket, role))
        logger.info(f"Client ({role}) connected to robot {robot_id}. Total active: {len(self.active_connections[robot_id])}")

    def disconnect(self, websocket: WebSocket, robot_id: str):
        if robot_id in self.active_connections:
            self.active_connections[robot_id] = [
                (ws, r) for ws, r in self.active_connections[robot_id] if ws is not websocket
            ]
            logger.info(f"Client disconnected from robot {robot_id}. Total active: {len(self.active_connections[robot_id])}")
            if not self.active_connections[robot_id]:
                del self.active_connections[robot_id]

    async def broadcast_to_robot(self, robot_id: str, message: dict):
        """Broadcasts a JSON message to ALL clients subscribed to this robot_id (regardless of role)."""
        if robot_id in self.active_connections:
            connections = list(self.active_connections[robot_id])
            for ws, role in connections:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to a websocket for robot {robot_id}: {e}")
                    self.disconnect(ws, robot_id)

    async def send_to_role(self, robot_id: str, role: str, message: dict, exclude: WebSocket = None):
        """Sends a JSON message only to connections of a specific role for a given robot_id."""
        logger.debug(f"send_to_role called for {robot_id} to role {role}")
        if robot_id in self.active_connections:
            connections = list(self.active_connections[robot_id])
            for ws, r in connections:
                if r == role and ws is not exclude:
                    try:
                        await ws.send_json(message)
                    except Exception as e:
                        logger.warning(f"Failed to send to {role} websocket for robot {robot_id}: {e}")
                        self.disconnect(ws, robot_id)
        else:
            logger.debug(f"No active connections for {robot_id}")

# Singleton instance
manager = ConnectionManager()
