from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from typing import Literal, Optional
from datetime import datetime

class SensorReadingCreate(BaseModel):
    # waypoint_id/phase are optional so the robot can also send live readings while
    # moving between waypoints. Each sensor value is optional so one broken sensor
    # doesn't get the whole reading rejected.
    model_config = ConfigDict(populate_by_name=True)

    robot_id: str = Field(..., description="The ID of the robot")
    waypoint_id: Optional[str] = Field(None, description="ObjectId string of the waypoint (omit for a live reading)")
    phase: Optional[Literal["before", "after"]] = Field(None, description="Reading taken before or after treatment (omit for a live reading)")
    turbidity_ntu: Optional[float] = Field(None, validation_alias=AliasChoices("turbidity_ntu", "turbidity"), description="Turbidity in NTU units")
    ph: Optional[float] = Field(None, description="pH scale 0-14")
    tds_ppm: Optional[float] = Field(None, validation_alias=AliasChoices("tds_ppm", "tds"), description="Total dissolved solids in ppm")
    temperature_celsius: Optional[float] = Field(None, validation_alias=AliasChoices("temperature_celsius", "temperature", "temperature_c"), description="Water temperature in °C")
    latitude: Optional[float] = Field(None, description="Where the reading was taken")
    longitude: Optional[float] = Field(None, description="Where the reading was taken")
    nir_floc_score: Optional[float] = Field(None, description="NIR-derived floc aggregation score")
    obstacle_detected: Optional[bool] = Field(None, description="SONAR detected an object nearby")
    sonar_distance_cm: Optional[float] = Field(None, description="Distance to nearest underwater object (cm)")

class SensorReadingOut(SensorReadingCreate):
    id: str = Field(..., description="MongoDB ObjectId as string")
    timestamp: datetime = Field(..., description="Server-set UTC timestamp")
    status: Literal["good", "borderline", "critical", "no_data"] = Field(..., description="Server-computed from turbidity_ntu and ph")
