from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime, timezone
from app.core.database import get_database
from app.core.auth import verify_api_key
from app.schemas.treatment_event import TreatmentEventCreate, TreatmentEventOut
from app.utils.bson import validate_object_id, serialize_doc

router = APIRouter(prefix="/api/treatment-events", tags=["Treatment Events"])

@router.post("/", response_model=TreatmentEventOut, status_code=status.HTTP_201_CREATED)
async def create_treatment_event(
    event: TreatmentEventCreate,
    api_key: str = Depends(verify_api_key)
):
    db = get_database()
    
    # Validate waypoint exists
    wp_oid = validate_object_id(event.waypoint_id)
    wp_doc = await db.waypoints.find_one({"_id": wp_oid})
    if not wp_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waypoint not found")
        
    doc = event.model_dump()
    doc["started_at"] = datetime.now(timezone.utc)
    doc["ended_at"] = None
    doc["outcome"] = None
    
    result = await db.treatment_events.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    return TreatmentEventOut(**serialize_doc(doc))

@router.get("/", response_model=List[TreatmentEventOut])
async def list_treatment_events(
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
        
    cursor = db.treatment_events.find(query).sort("started_at", -1).limit(min(limit, 200))
    events = await cursor.to_list(length=200)
    
    return [TreatmentEventOut(**serialize_doc(e)) for e in events]

@router.get("/{id}", response_model=TreatmentEventOut)
async def get_treatment_event(id: str):
    db = get_database()
    oid = validate_object_id(id)
    
    doc = await db.treatment_events.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treatment event not found")
        
    return TreatmentEventOut(**serialize_doc(doc))
