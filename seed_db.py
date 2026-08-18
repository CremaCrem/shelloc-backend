import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

# We assume standard MongoDB connection string as in settings
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.shelloc_db

async def seed_robot():
    robot_id = "SHELLOC-01"
    
    seed_data = {
        "robot_id": robot_id,
        "battery_percent": 100,
        "gps_signal": "strong",
        "current_lat": 14.59972,
        "current_lng": 120.98491,
        "heading_deg": 45.0,
        "speed_knots": 0.0,
        "flocculant_ml": 500,
        "mission_state": "idle",
        "is_active": False,
        "last_sync": datetime.now(timezone.utc),
        "overall_status": "operational"
    }
    
    await db.robot_status.update_one(
        {"robot_id": robot_id},
        {"$set": seed_data},
        upsert=True
    )
    print("Seeded SHELLOC-01 initial status successfully.")

if __name__ == "__main__":
    asyncio.run(seed_robot())
