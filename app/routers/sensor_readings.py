from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime, timezone
from app.core.database import get_database
from app.core.auth import verify_api_key
from app.schemas.sensor_reading import SensorReadingCreate, SensorReadingOut
from app.utils.bson import validate_object_id, serialize_doc

router = APIRouter(prefix="/api/sensor-readings", tags=["Sensor Readings"])

def compute_sensor_status(turbidity_ntu: float) -> str:
    if turbidity_ntu < 20:
        return "good"
    elif turbidity_ntu <= 50:
        return "borderline"
    else:
        return "critical"

@router.post("/", response_model=SensorReadingOut, status_code=status.HTTP_201_CREATED)
async def create_sensor_reading(
    reading: SensorReadingCreate,
    api_key: str = Depends(verify_api_key)
):
    db = get_database()
    
    # Validate waypoint exists
    wp_oid = validate_object_id(reading.waypoint_id)
    wp_doc = await db.waypoints.find_one({"_id": wp_oid})
    if not wp_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waypoint not found")
        
    doc = reading.model_dump()
    doc["timestamp"] = datetime.now(timezone.utc)
    doc["status"] = compute_sensor_status(reading.turbidity_ntu)
    
    result = await db.sensor_readings.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    return SensorReadingOut(**serialize_doc(doc))

@router.get("/latest", response_model=List[SensorReadingOut])
async def get_latest_readings(robot_id: str):
    """
    Returns the single most recent reading per waypoint for the specified robot.
    """
    db = get_database()
    
    pipeline = [
        {"$match": {"robot_id": robot_id}},
        {"$sort": {"timestamp": -1}},
        {
            "$group": {
                "_id": "$waypoint_id",
                "latest_reading": {"$first": "$$ROOT"}
            }
        },
        {"$replaceRoot": {"newRoot": "$latest_reading"}}
    ]
    
    cursor = db.sensor_readings.aggregate(pipeline)
    readings = await cursor.to_list(length=200)
    
    return [SensorReadingOut(**serialize_doc(r)) for r in readings]

@router.get("/", response_model=List[SensorReadingOut])
async def list_sensor_readings(
    robot_id: Optional[str] = None,
    waypoint_id: Optional[str] = None,
    limit: int = 50
):
    db = get_database()
    query = {}
    if robot_id:
        query["robot_id"] = robot_id
    if waypoint_id:
        query["waypoint_id"] = waypoint_id
        
    cursor = db.sensor_readings.find(query).sort("timestamp", -1).limit(min(limit, 200))
    readings = await cursor.to_list(length=200)
    
    return [SensorReadingOut(**serialize_doc(r)) for r in readings]

@router.get("/{id}", response_model=SensorReadingOut)
async def get_sensor_reading(id: str):
    db = get_database()
    oid = validate_object_id(id)
    
    doc = await db.sensor_readings.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor reading not found")
        
    return SensorReadingOut(**serialize_doc(doc))
