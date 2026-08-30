from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime, timezone
from app.core.database import get_database
from app.schemas.waypoint import WaypointCreate, WaypointUpdate, WaypointOut, WaypointDetailOut
from app.utils.bson import validate_object_id, serialize_doc

router = APIRouter(prefix="/api/waypoints", tags=["Waypoints"])

@router.post("/", response_model=WaypointOut, status_code=status.HTTP_201_CREATED)
async def create_waypoint(waypoint: WaypointCreate):
    db = get_database()
    
    # Enforce max 6 waypoints per robot
    count = await db.waypoints.count_documents({"robot_id": waypoint.robot_id})
    if count >= 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Robot {waypoint.robot_id} already has the maximum of 6 waypoints."
        )
    
    doc = waypoint.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    doc["treated"] = False
    doc["treated_at"] = None
    doc["before_reading_id"] = None
    doc["after_reading_id"] = None
    
    # Handle optional label
    if doc.get("label") is None:
        doc["label"] = f"Point {doc['point_number']}"
        
    result = await db.waypoints.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    return WaypointOut(**serialize_doc(doc))

@router.get("/", response_model=List[WaypointOut])
async def list_waypoints(robot_id: str = None, limit: int = 50):
    db = get_database()
    query = {}
    if robot_id:
        query["robot_id"] = robot_id
        
    cursor = db.waypoints.find(query).limit(min(limit, 200))
    waypoints = await cursor.to_list(length=200)
    
    return [WaypointOut(**serialize_doc(wp)) for wp in waypoints]
@router.get("/robot/{robot_id}", response_model=List[WaypointOut])
async def list_waypoints_by_robot(robot_id: str, limit: int = 50):
    db = get_database()
    cursor = db.waypoints.find({"robot_id": robot_id}).limit(min(limit, 200))
    waypoints = await cursor.to_list(length=200)
    return [WaypointOut(**serialize_doc(wp)) for wp in waypoints]

@router.get("/{id}", response_model=WaypointDetailOut)
async def get_waypoint(id: str):
    db = get_database()
    oid = validate_object_id(id)
    
    waypoint = await db.waypoints.find_one({"_id": oid})
    if not waypoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waypoint not found")
        
    # Resolve linked readings
    before_reading = None
    if waypoint.get("before_reading_id"):
        b_oid = validate_object_id(waypoint["before_reading_id"])
        b_doc = await db.sensor_readings.find_one({"_id": b_oid})
        before_reading = serialize_doc(b_doc)
        
    after_reading = None
    if waypoint.get("after_reading_id"):
        a_oid = validate_object_id(waypoint["after_reading_id"])
        a_doc = await db.sensor_readings.find_one({"_id": a_oid})
        after_reading = serialize_doc(a_doc)
        
    serialized_wp = serialize_doc(waypoint)
    serialized_wp["before_reading"] = before_reading
    serialized_wp["after_reading"] = after_reading
    
    return WaypointDetailOut(**serialized_wp)

@router.patch("/{id}", response_model=WaypointOut)
async def update_waypoint(id: str, update_data: WaypointUpdate):
    db = get_database()
    oid = validate_object_id(id)
    
    existing = await db.waypoints.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waypoint not found")
        
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return WaypointOut(**serialize_doc(existing))
        
    await db.waypoints.update_one({"_id": oid}, {"$set": update_dict})
    
    updated_doc = await db.waypoints.find_one({"_id": oid})
    return WaypointOut(**serialize_doc(updated_doc))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_waypoint(id: str):
    db = get_database()
    oid = validate_object_id(id)
    
    result = await db.waypoints.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waypoint not found")
    
    return None
