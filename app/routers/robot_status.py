from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone
from typing import Optional

from app.core.auth import verify_api_key
from app.core.database import get_database
from app.schemas.robot_status import RobotStatusUpdate, RobotStatusOut

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
    
    # Prepare the document for MongoDB
    update_doc = status_update.model_dump()
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
    except Exception as e:
        # Avoid exposing raw database errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update robot status in the database."
        )
    
    # Prepare the response
    return RobotStatusOut(**update_doc)

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
