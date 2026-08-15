from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class TreatmentEventCreate(BaseModel):
    robot_id: str = Field(..., description="The ID of the robot")
    waypoint_id: str = Field(..., description="ObjectId string of the waypoint")
    dosage_ml: float = Field(..., description="Volume of flocculant dispensed (mL)")
    pollution_level: Literal["low", "medium", "high"] = Field(..., description="Robot-assessed pollution level")
    floc_aggregation_time_sec: Optional[int] = Field(None, description="Time for floc to form (seconds)")
    eta_next_area_sec: Optional[int] = Field(None, description="Estimated travel time to next waypoint")

class TreatmentEventOut(TreatmentEventCreate):
    id: str = Field(..., description="MongoDB ObjectId as string")
    started_at: datetime = Field(..., description="Server-set UTC insert time")
    ended_at: Optional[datetime] = Field(None, description="Nullable")
    outcome: Optional[Literal["collected", "recollection_needed"]] = Field(None, description="Nullable")
