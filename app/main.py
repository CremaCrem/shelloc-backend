from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.core.database import get_database
from app.routers import robot_status, waypoints, sensor_readings, treatment_events, ai_chat

app = FastAPI(title="SHELLOC Backend API")

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Basic health check for the FastAPI application and MongoDB connectivity.
    """
    try:
        # Ping the database
        db = get_database()
        await db.command("ping")
        db_status = "ok"
    except Exception as e:
        db_status = "error"
        # In a real app we might log the exception securely here
    
    status_code = 200 if db_status == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "app_status": "ok",
            "database_status": db_status
        }
    )

app.include_router(robot_status.router)
app.include_router(waypoints.router)
app.include_router(sensor_readings.router)
app.include_router(treatment_events.router)
app.include_router(ai_chat.router)
