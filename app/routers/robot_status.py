from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone
from typing import Optional

from app.core.auth import verify_api_key
from app.core.database import get_database
from app.schemas.robot_status import RobotStatusUpdate, RobotStatusOut, RobotStatusDispatch
from app.utils.bson import validate_object_id
from app.services.connection_manager import manager

router = APIRouter(prefix="/api/robot-status", tags=["Robot Status"])

def compute_overall_status(battery_percent: int, gps_signal: Optional[str]) -> str:
    """
    Computes the overall_status of the robot based on battery and GPS.
    """
    low_batt = battery_percent < 20
    no_gps = gps_signal == "none"
    
    if low_batt and no_gps:
        return "degraded"
    elif low_batt:
        return "low_battery"
    elif no_gps:
        return "gps_lost"
    else:
        return "operational"

@router.post("/{robot_id}", response_model=RobotStatusOut, status_code=status.HTTP_200_OK)
async def update_robot_status(
    robot_id: str,
    status_update: RobotStatusUpdate,
    api_key: str = Depends(verify_api_key)
):
    """
    Upserts the robot status document.
    Requires X-API-Key authentication.
    """
    db = get_database()
    
    # Server-computed fields
    last_sync = datetime.now(timezone.utc)
    overall_status = compute_overall_status(
        battery_percent=status_update.battery_percent,
        gps_signal=status_update.gps_signal
    )
    
    # Prepare the document for MongoDB using exclude_unset to avoid overwriting fields like target_waypoint_id
    update_doc = status_update.model_dump(exclude_unset=True)
    update_doc["last_sync"] = last_sync
    update_doc["overall_status"] = overall_status
    
    # We don't store robot_id as a separate field inside the document if we use it as _id, 
    # but for simplicity and indexing let's just store it as a field and query by it.
    update_doc["robot_id"] = robot_id
    
    try:
        # Upsert: update existing doc with this robot_id, or insert if it doesn't exist
        await db.robot_status.update_one(
            {"robot_id": robot_id},
            {"$set": update_doc},
            upsert=True
        )
        # Fetch the updated document to include fields that were not overwritten
        updated_doc = await db.robot_status.find_one({"robot_id": robot_id})
    except Exception as e:
        # Avoid exposing raw database errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update robot status in the database."
        )
    
    # Prepare the response
    response_out = RobotStatusOut(**updated_doc)
    
    # Broadcast to any connected websocket clients
    await manager.broadcast_to_robot(robot_id, response_out.model_dump(mode="json"))
    
    return response_out

@router.get("/{robot_id}", response_model=RobotStatusOut)
async def get_robot_status(robot_id: str):
    """
    Retrieves the latest robot status. No authentication required.
    """
    db = get_database()
    
    try:
        doc = await db.robot_status.find_one({"robot_id": robot_id})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query robot status from the database."
        )
        
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No status found for robot '{robot_id}'"
        )
        
    return RobotStatusOut(**doc)

@router.patch("/{robot_id}", response_model=RobotStatusOut)
async def dispatch_robot(robot_id: str, dispatch_update: RobotStatusDispatch):
    """
    Dispatches the robot to a specific waypoint by setting target_waypoint_id.
    """
    db = get_database()
    
    # Verify robot exists
    robot_doc = await db.robot_status.find_one({"robot_id": robot_id})
    if not robot_doc:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")

    if dispatch_update.target_waypoint_id is not None:
        # Validate waypoint exists
        wp_oid = validate_object_id(dispatch_update.target_waypoint_id)
        wp_doc = await db.waypoints.find_one({"_id": wp_oid})
        if not wp_doc:
            raise HTTPException(status_code=404, detail="Target waypoint not found")
            
        # Check mission state
        current_state = robot_doc.get("mission_state", "idle")
        if current_state not in ["idle", "completed"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot dispatch. Robot is currently in state: {current_state}"
            )
        
        updates = {
            "target_waypoint_id": dispatch_update.target_waypoint_id,
            # We do NOT set mission_state="navigating" here. 
            # The robot reads target_waypoint_id and sets its own state on next heartbeat.
        }
    else:
        # Cancel target
        updates = {
            "target_waypoint_id": None,
            "mission_state": "idle"
        }

    await db.robot_status.update_one(
        {"robot_id": robot_id},
        {"$set": updates}
    )
    
    # Return updated doc
    updated_doc = await db.robot_status.find_one({"robot_id": robot_id})
    response_out = RobotStatusOut(**updated_doc)
    
    # Broadcast to any connected websocket clients
    await manager.broadcast_to_robot(robot_id, response_out.model_dump(mode="json"))
    
    return response_out
