# Development Guide

This guide covers local development setup, testing, and contribution conventions.

## 1. Prerequisites
- Python 3.11+
- MongoDB running locally on port 27017
- An AI provider API key (OpenAI, Claude, or Gemini)

## 2. Local Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your values for MONGO_URI, DB_NAME, AI_PROVIDER, AI_API_KEY, API_KEY

# 4. Run the development server
uvicorn app.main:app --reload --port 8000
```

## 3. Testing the API

### Swagger UI
Open [http://localhost:8000/docs](http://localhost:8000/docs). This is the interactive Swagger UI.

### Authentication
Robot-facing write endpoints require the `X-API-Key` header.
In the Swagger UI, click the **Authorize** button and enter your `.env` `API_KEY` to test these endpoints.

## 4. Code Conventions

- **Module Naming**: Use lowercase `snake_case` for all Python files. Pluralize router names (e.g., `sensor_readings.py`).
- **Imports**: Avoid circular dependencies. Use absolute imports (e.g., `from app.core.database import get_database`).
- **Async**: Use Motor's async `await` API. Never call synchronous blocking IO inside FastAPI route handlers.
- **Routers vs Services**: Keep routers thin. Put complex business logic or cross-collection aggregations into `services/`.
- **Adding a new endpoint**:
  1. Add request/response models in `app/schemas/`.
  2. Document the internal MongoDB structure in `app/models/` (if necessary for typing).
  3. Implement the route in `app/routers/`.
  4. Ensure any required server-computed fields are handled.
  5. Update `docs/api-reference.md`.
