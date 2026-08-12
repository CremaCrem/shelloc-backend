from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import asyncio

_clients = {}

def get_database():
    """
    Returns the MongoDB async database instance.
    Initializes the client per event loop to support testing with TestClient.
    """
    loop = asyncio.get_running_loop()
    if loop not in _clients:
        _clients[loop] = AsyncIOMotorClient(settings.MONGO_URI)
    return _clients[loop][settings.DB_NAME]
