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


# Robots currently being driven from the app. Lets us mark manual_override once
# instead of writing to the DB on every joystick packet (5-10 per second).
# ponytail: in-memory, assumes a single server process (same as the connection manager).
_manual_robots = set()


async def _handle_manual_control(websocket: WebSocket, robot_id: str, payload: dict):
    """Validate joystick data and relay to edge connections only."""
    data = payload.get("data")
    if not isinstance(data, dict) or not _validate_joystick(data):
        logger.warning(f"Invalid manual_control payload for {robot_id}: {payload}")
        return  # silently drop invalid payloads
    await manager.send_to_role(robot_id, "edge", payload, exclude=websocket)

    # Record the takeover ourselves so the app shows MANUAL and resume works,
    # even if the robot firmware never reports manual_override.
    if robot_id not in _manual_robots:
        _manual_robots.add(robot_id)
        await get_database().robot_status.update_one(
            {"robot_id": robot_id},
            {"$set": {"mission_state": "manual_override", "operation_mode": "manual"}},
        )


async def _handle_resume_autonomous(robot_id: str):
    """Tell the robot to leave manual mode. If a waypoint is active, resume navigation.

    The command is always forwarded to the robot — a robot that is still being driven
    must hear "stop manual", whatever the stored state says.
    """
    logger.debug(f"resume_autonomous called for {robot_id}")
    _manual_robots.discard(robot_id)
    db = get_database()
    doc = await db.robot_status.find_one({"robot_id": robot_id}) or {}

    target_wp = doc.get("target_waypoint_id")
    target_wp = str(target_wp) if target_wp else None

    # Firmware doc names this event "resume_autonomous"; older backend contract
    # used "resume_navigation". Send both so either firmware version reacts.
    await manager.send_to_role(robot_id, "edge", {
        "event": "resume_autonomous",
        "waypoint_id": target_wp,
    })
    if target_wp:
        await manager.send_to_role(robot_id, "edge", {
            "event": "resume_navigation",
            "waypoint_id": target_wp,
        })

    # Only move the stored state if it still says manual; otherwise the robot's own
    # heartbeat already reported something newer and is the source of truth.
    if doc.get("mission_state") == "manual_override":
        await db.robot_status.update_one(
            {"robot_id": robot_id},
            {"$set": {
                "mission_state": "navigating" if target_wp else "idle",
                "operation_mode": "autonomous",
            }}
        )


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
        if role == "mobile":
            # Next joystick session marks manual_override again.
            _manual_robots.discard(robot_id)
