from app.core.database import get_database
from app.core.config import settings

async def build_context(robot_id: str) -> dict:
    """
    Summarizes latest robot status, waypoints, and sensor readings for the AI.
    """
    db = get_database()
    context = {"robot_id": robot_id}
    
    # 1. Get robot status
    robot_doc = await db.robot_status.find_one({"robot_id": robot_id})
    if robot_doc:
        robot_doc.pop("_id", None)
        context["robot_status"] = robot_doc
        
    # 2. Get waypoints
    waypoints_cursor = db.waypoints.find({"robot_id": robot_id})
    waypoints = await waypoints_cursor.to_list(length=10)
    for wp in waypoints:
        wp["id"] = str(wp.pop("_id"))
    context["waypoints"] = waypoints
    
    # 3. Get latest sensor reading per waypoint (using same pipeline as /latest)
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
    readings_cursor = db.sensor_readings.aggregate(pipeline)
    readings = await readings_cursor.to_list(length=10)
    for r in readings:
        r["id"] = str(r.pop("_id"))
        r["_id"] = r["id"] # temporary hack to keep objectid string for output
    context["latest_sensor_readings"] = readings
    
    return context

async def get_ai_reply(message: str, context: dict) -> str:
    """
    Calls the configured AI provider. Uses a fallback if no API key is provided.
    """
    if not settings.AI_API_KEY:
        return (
            f"[Mock AI Response] Based on the context provided for robot {context.get('robot_id')}, "
            f"it is currently in {context.get('robot_status', {}).get('mission_state', 'unknown')} state. "
            f"You asked: '{message}'"
        )
        
    # Example logic for real provider
    provider = settings.AI_PROVIDER
    # if provider == "openai": ...
    # elif provider == "claude": ...
    # elif provider == "gemini": ...
    
    return f"This is a mocked response from {provider} for the query: '{message}'."
