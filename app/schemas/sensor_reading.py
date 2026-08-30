from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class SensorReadingCreate(BaseModel):
    robot_id: str = Field(..., description="The ID of the robot")
    waypoint_id: str = Field(..., description="ObjectId string of the waypoint")
    phase: Literal["before", "after"] = Field(..., description="Reading taken before or after treatment")
    turbidity_ntu: float = Field(..., description="Turbidity in NTU units")
    ph: float = Field(..., description="pH scale 0-14")
    tds_ppm: float = Field(..., description="Total dissolved solids in ppm")
    nir_floc_score: Optional[float] = Field(None, description="NIR-derived floc aggregation score")

class SensorReadingOut(SensorReadingCreate):
    id: str = Field(..., description="MongoDB ObjectId as string")
    timestamp: datetime = Field(..., description="Server-set UTC timestamp")
    status: Literal["good", "borderline", "critical", "no_data"] = Field(..., description="Server-computed from turbidity_ntu and ph")
