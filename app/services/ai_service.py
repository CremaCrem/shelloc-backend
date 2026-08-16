from app.core.database import get_database
from app.core.config import settings
from google import genai
from google.genai import types

MAX_CHAT_HISTORY = 5

SYSTEM_INSTRUCTION = """
You are the SHELLOC System Assistant, an intelligent agent monitoring a turtle-like autonomous water treatment robot. 
Your goal is to provide concise, conversational answers about the robot's status, telemetry, and water quality readings.

Here are the operational parameters:
- Turbidity (NTU): <20 NTU = good/remediated (monitoring only); 20-50 NTU = borderline; >50 NTU = critical/severe (requires active treatment). Untreated baseline is typically 110.33-146.51 NTU, and post-treatment target is 10.40-16.25 NTU.
- pH: <6.0 = acidic/degraded (requires stabilization); 6.0-7.0 = target stabilized post-treatment window (mean ~6.46); >7.5-8.5 = borderline/elevated alkaline. Untreated baseline is typically 4.95-6.03.
- TDS (ppm): >400 ppm = high dissolved particulate load; ~200-250 ppm = target remediated state. Untreated baseline is typically 394.16-485.13 ppm, and post-treatment target is 197.16-243.12 ppm.
- Flocculant Dosage (Moringa-Chitosan): Adaptive dosage based on turbidity. If <20 NTU: no additional flocculant, monitoring only. If 20-50 NTU: moderate dosage via pump. If >50 NTU (or baseline >100 NTU): full/maximum standard dosage for rapid macro-floc aggregation.
- Geofence Boundary: 2-meter radius from the target waypoint.

When providing a concrete recommendation (like a dosage value, a status verdict, or actionable advice), format it clearly so it stands out. For example, use bolding or a labeled line:
**Recommendation:** Increase dosage to X mL.

Keep your responses conversational but grounded entirely in the provided JSON context snippet. Do not invent readings that are not in the context, but if the user provides hypothetical readings, answer based on the rules.
"""

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
    
    # 3. Get latest sensor reading per waypoint
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

async def get_ai_reply(message: str, context: dict, user_id: str = None) -> str:
    """
    Calls the configured AI provider. Uses a fallback if no API key is provided.
    Fetches up to MAX_CHAT_HISTORY recent messages to inject as conversational memory.
    """
    if not settings.AI_API_KEY:
        return (
            f"[Mock AI Response] Based on the context provided for robot {context.get('robot_id')}, "
            f"it is currently in {context.get('robot_status', {}).get('mission_state', 'unknown')} state. "
            f"You asked: '{message}'"
        )
        
    if settings.AI_PROVIDER != "gemini":
        return f"Provider {settings.AI_PROVIDER} is not fully implemented yet."
        
    db = get_database()
    history_contents = []
    
    if user_id:
        # Fetch the most recent MAX_CHAT_HISTORY messages for this user, sorted oldest first in this batch
        cursor = db.ai_chat_logs.find({"user_id": user_id}).sort("timestamp", -1).limit(MAX_CHAT_HISTORY)
        recent_msgs = await cursor.to_list(length=MAX_CHAT_HISTORY)
        recent_msgs.reverse() # Oldest first for the context window
        
        for msg in recent_msgs:
            role = "user" if msg["role"] == "user" else "model"
            history_contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg["message"])])
            )
            
    # Add the current message with the injected context
    context_str = str(context)
    full_prompt = f"System Context Snapshot:\n{context_str}\n\nUser Question:\n{message}"
    history_contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)])
    )
    
    try:
        client = genai.Client(api_key=settings.AI_API_KEY)
        response = client.models.generate_content(
            model='gemini-3.7-flash',
            contents=history_contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.4
            )
        )
        return response.text
    except Exception as e:
        return f"**Error:** I'm having trouble connecting to the AI provider right now. ({str(e)})"
