import os
import re

files = [
    "tests/test_ai_chat.py",
    "tests/test_robot_status.py",
    "tests/test_sensor_readings.py",
    "tests/test_treatment_events.py",
    "tests/test_waypoints.py",
]

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    # Prepend uuid generation if not there
    if "import uuid" not in content:
        content = "import uuid\n" + content
    
    # We want to replace specific test strings with f-strings or concatenated strings using uuid,
    # OR simpler: just replace "robot_1" and "test_robot_..." with a randomly generated literal for THIS script run,
    # BUT wait: if we do that, the literal is static, so if pytest is run TWICE, it still collides!
    # It needs to be dynamic at RUNTIME.
    
    # We can replace literal strings with variables that we define.
    # Actually, the simplest fix is to just append `+ str(uuid.uuid4())[:8]` everywhere we define a robot ID.
    
    # But replacing inside JSON blobs requires it to not be a literal anymore.
    # The safest is to rewrite the tests properly.
