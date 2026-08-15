from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class WaypointCreate(BaseModel):
    robot_id: str = Field(..., description="The ID of the robot this waypoint belongs to")
    point_number: int = Field(..., ge=1, le=6, description="1-based index of the waypoint (max 6)")
    latitude: float = Field(..., description="Decimal degrees latitude")
    longitude: float = Field(..., description="Decimal degrees longitude")
    label: Optional[str] = Field(None, description="Optional label, defaults to 'Point {point_number}'")
    radius_meters: float = Field(2.0, description="Boundary radius around the waypoint center. Defaults to 2.0")

class WaypointUpdate(BaseModel):
    treated: Optional[bool] = Field(None, description="Whether this waypoint has been treated")
    before_reading_id: Optional[str] = Field(None, description="ObjectId string of the before treatment sensor reading")
    after_reading_id: Optional[str] = Field(None, description="ObjectId string of the after treatment sensor reading")
    treated_at: Optional[datetime] = Field(None, description="UTC timestamp when treatment completed")

class WaypointOut(WaypointCreate):
    id: str = Field(..., description="MongoDB ObjectId as string")
    created_at: datetime = Field(..., description="Server-set UTC timestamp")
    treated: bool = Field(False, description="Whether this waypoint has been treated")
    treated_at: Optional[datetime] = Field(None, description="UTC timestamp when treatment completed")
    before_reading_id: Optional[str] = Field(None, description="ObjectId string of the before treatment sensor reading")
    after_reading_id: Optional[str] = Field(None, description="ObjectId string of the after treatment sensor reading")

class WaypointDetailOut(WaypointOut):
    before_reading: Optional[dict] = Field(None, description="Inlined before_reading document")
    after_reading: Optional[dict] = Field(None, description="Inlined after_reading document")
