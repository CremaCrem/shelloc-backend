import os
import pytest
from pymongo import MongoClient

# Must set the environment variable before importing app modules that might depend on it
os.environ["DB_NAME"] = "shelloc_test"

# Import settings to modify it for already-loaded modules if any
from app.core.config import settings
settings.DB_NAME = "shelloc_test"

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Ensure the test database is clean before running the test suite.
    This replaces the previous manual teardown logic in individual files.
    """
    sync_client = MongoClient(settings.MONGO_URI)
    db = sync_client[settings.DB_NAME]
    
    # Drop the entire test database to start fresh
    sync_client.drop_database(settings.DB_NAME)
    
    yield
    
    # Optional: drop after tests too
    sync_client.drop_database(settings.DB_NAME)
    sync_client.close()
