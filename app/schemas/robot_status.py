from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class RobotStatusUpdate(BaseModel):
    operation_mode: Literal["autonomous", "manual"] = Field(..., description="The current operation mode of the robot")
    gps_signal: Optional[Literal["good", "weak", "none"]] = Field(None, description="Quality of the GPS signal")
    current_lat: Optional[float] = Field(None, description="Current latitude")
    current_lng: Optional[float] = Field(None, description="Current longitude")
    battery_percent: int = Field(..., ge=0, le=100, description="Battery percentage (0-100)")
    points_treated_today: int = Field(0, description="Number of waypoints treated today")
    target_waypoint_id: Optional[str] = Field(None, description="ObjectId string of the target waypoint, if dispatched")
    mission_state: Literal[
        "idle", 
        "navigating", 
        "baseline_evaluating", 
        "dispensing_flocculant", 
        "incubating_15m", 
        "mesh_biochar_filtering", 
        "post_evaluating", 
        "adaptive_stabilization", 
        "completed", 
        "failsafe_buoyancy"
    ] = Field("idle", description="The robot's current mission phase")

class RobotStatusDispatch(BaseModel):
    target_waypoint_id: Optional[str] = Field(None, description="ObjectId string of the waypoint to dispatch the robot to. Null to cancel active target.")

class RobotStatusOut(RobotStatusUpdate):
    robot_id: str = Field(..., description="The unique identifier for the robot")
    last_sync: datetime = Field(..., description="Server-computed UTC timestamp of the last heartbeat")
    overall_status: str = Field(..., description="Server-computed overall status (e.g., operational, low_battery, gps_lost, degraded)")

