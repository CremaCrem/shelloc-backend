import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    def __init__(self):
        self.MONGO_URI = os.getenv("MONGO_URI")
        self.DB_NAME = os.getenv("DB_NAME")
        self.API_KEY = os.getenv("API_KEY")
        self.AI_PROVIDER = os.getenv("AI_PROVIDER")
        self.AI_API_KEY = os.getenv("AI_API_KEY")
        self.AI_MODEL = os.getenv("AI_MODEL", "gemini-3.6-flash")
        
        # CORS allowed origins (comma-separated or wildcard default)
        cors_raw = os.getenv("CORS_ORIGINS", "*")
        self.CORS_ORIGINS = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]

        self.validate()

    def validate(self):
        missing_vars = []
        if not self.MONGO_URI:
            missing_vars.append("MONGO_URI")
        if not self.DB_NAME:
            missing_vars.append("DB_NAME")
        if not self.API_KEY:
            missing_vars.append("API_KEY")
        # AI_PROVIDER can remain configurable but we don't necessarily need to require AI_API_KEY to start
        # if not self.AI_PROVIDER:
        #     missing_vars.append("AI_PROVIDER")

        if missing_vars:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please ensure they are set in the .env file."
            )

# Create a single global instance of Settings
settings = Settings()
