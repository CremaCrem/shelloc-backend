from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
from typing import Literal, Optional
from datetime import datetime

MissionState = Literal[
    "idle",
    "navigating",
    "baseline_evaluating",
    "dispensing_flocculant",
    "incubating_15m",
    "mesh_biochar_filtering",
    "post_evaluating",
    "adaptive_stabilization",
    "completed",
    "failsafe_buoyancy",
    "manual_override"
]

class RobotStatusUpdate(BaseModel):
    # Robot firmware is developed separately, so the heartbeat is lenient: every field
    # is optional (missing ones keep their last stored value) and the older names from
    # the firmware doc example (gps_lat / gps_lng / status) are accepted too.
    model_config = ConfigDict(populate_by_name=True)

    operation_mode: Optional[Literal["autonomous", "manual"]] = Field(None, description="The current operation mode of the robot")
    gps_signal: Optional[Literal["good", "weak", "none"]] = Field(None, description="Quality of the GPS signal")
    current_lat: Optional[float] = Field(None, validation_alias=AliasChoices("current_lat", "gps_lat"), description="Current latitude")
    current_lng: Optional[float] = Field(None, validation_alias=AliasChoices("current_lng", "gps_lng"), description="Current longitude")
    heading_degrees: Optional[float] = Field(None, description="Robot heading in degrees (0-360)")
    battery_percent: Optional[float] = Field(None, description="Battery percentage (0-100)")
    points_treated_today: int = Field(0, description="Number of waypoints treated today")
    target_waypoint_id: Optional[str] = Field(None, description="ObjectId string of the target waypoint, if dispatched")
    mission_state: MissionState = Field("idle", validation_alias=AliasChoices("mission_state", "status"), description="The robot's current mission phase")
    flocculant_tank_percent: Optional[float] = Field(None, ge=0, le=100, description="Moringa-chitosan tank level (0-100)")
    citric_acid_tank_percent: Optional[float] = Field(None, ge=0, le=100, description="Citric acid tank level (0-100)")
    biochar_health_status: Optional[Literal["optimal", "degraded", "replace"]] = Field(None, description="Biochar filter condition")
    timer_remaining_sec: Optional[int] = Field(None, ge=0, description="Seconds left in the incubation countdown")
    buoyancy_failsafe_active: Optional[bool] = Field(None, description="True while the buoyancy failsafe is triggered")

    @field_validator("battery_percent")
    @classmethod
    def clamp_battery(cls, v):
        # A slightly-off reading (e.g. 101) shouldn't reject the whole heartbeat.
        return None if v is None else max(0.0, min(100.0, v))

    @field_validator("heading_degrees")
    @classmethod
    def wrap_heading(cls, v):
        # Accept -90 or 450 and store as 0-360.
        return None if v is None else v % 360

class RobotStatusDispatch(BaseModel):
    target_waypoint_id: Optional[str] = Field(None, description="ObjectId string of the waypoint to dispatch the robot to. Null to cancel active target.")

class RobotStatusOut(RobotStatusUpdate):
    robot_id: str = Field(..., description="The unique identifier for the robot")
    last_sync: datetime = Field(..., description="Server-computed UTC timestamp of the last heartbeat")
    overall_status: str = Field(..., description="Server-computed overall status (e.g., operational, low_battery, gps_lost, degraded)")
