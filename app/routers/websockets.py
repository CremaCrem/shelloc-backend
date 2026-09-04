import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.connection_manager import manager
from app.core.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_joystick(data: dict) -> bool:
    """Returns True if x and y are both within [-1.0, 1.0]."""
    x = data.get("x")
    y = data.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return False
    return -1.0 <= x <= 1.0 and -1.0 <= y <= 1.0


async def _handle_manual_control(websocket: WebSocket, robot_id: str, payload: dict):
    """Validate joystick data and relay to edge connections only."""
    data = payload.get("data")
    if not isinstance(data, dict) or not _validate_joystick(data):
        logger.warning(f"Invalid manual_control payload for {robot_id}: {payload}")
        return  # silently drop invalid payloads
    await manager.send_to_role(robot_id, "edge", payload, exclude=websocket)


async def _handle_resume_autonomous(robot_id: str):
    """Transition back to autonomous mode. If a waypoint is active, resume navigation."""
    logger.debug(f"resume_autonomous called for {robot_id}")
    db = get_database()
    doc = await db.robot_status.find_one({"robot_id": robot_id})
    if not doc:
        return

    # Guard: only act if currently in manual_override
    if doc.get("mission_state") != "manual_override":
        logger.info(f"Ignoring resume_autonomous for {robot_id}: not in manual_override state")
        return

    target_wp = doc.get("target_waypoint_id")
    if target_wp:
        # Active waypoint exists — set state to navigating and tell edge to resume
        await db.robot_status.update_one(
            {"robot_id": robot_id},
            {"$set": {"mission_state": "navigating"}}
        )
        await manager.send_to_role(robot_id, "edge", {
            "event": "resume_navigation",
            "waypoint_id": str(target_wp),
        })
    else:
        # No active waypoint — just return to idle
        await db.robot_status.update_one(
            {"robot_id": robot_id},
            {"$set": {"mission_state": "idle"}}
        )
        logger.debug(f"State set to idle for robot {robot_id}.")


@router.websocket("/ws/robot/{robot_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    robot_id: str,
    role: str = Query("mobile"),
):
    """
    Establish a WebSocket connection to stream live telemetry for a specific robot.

    Query params:
        role: 'mobile' or 'edge'. Controls message routing.
    """
    await manager.connect(websocket, robot_id, role)
    try:
        while True:
            raw = await websocket.receive_text()

            # --- Parse JSON ---
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Non-JSON message from {role} on robot {robot_id}: {raw!r}")
                continue

            if not isinstance(payload, dict):
                continue

            event = payload.get("event")
            if not event:
                logger.debug(f"Message without 'event' field from {role} on robot {robot_id}")
                continue

            # --- Route by event type ---
            if event == "manual_control":
                await _handle_manual_control(websocket, robot_id, payload)
            elif event == "resume_autonomous":
                await _handle_resume_autonomous(robot_id)
            else:
                logger.debug(f"Unknown event '{event}' from {role} on robot {robot_id}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, robot_id)
