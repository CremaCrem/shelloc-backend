# Development Guide

This guide covers local development setup, Docker containerization, testing, and contribution conventions.

## 1. Prerequisites
- Python 3.11+ (for local native development) or Docker & Docker Compose
- MongoDB connection string (e.g. MongoDB Atlas or local MongoDB instance)
- Google Gemini API key (`AI_API_KEY`)

### Key Dependencies
- `fastapi`, `uvicorn`: Web framework and ASGI server.
- `motor`, `pymongo`: Async MongoDB driver.
- `google-genai`: Official Google Generative AI SDK for live LLM responses (Phase 3).
- `pytest`, `httpx`: Automated testing framework and async HTTP test client (Phase 2).

---

## 2. Local Setup (Native Python)

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

---

## 3. Running via Docker

The repository includes a containerized development environment via `Dockerfile` and `docker-compose.yml`.

> [!NOTE]
> `docker-compose.yml` does **not** spin up a local MongoDB container. Instead, the backend connects to the database specified by `MONGO_URI` in your `.env` file (such as MongoDB Atlas).

### Docker Commands

```bash
# 1. Build the container image
docker compose build

# 2. Start the backend in the background
docker compose up -d

# 3. View live container logs
docker compose logs -f backend

# 4. Run the automated test suite inside the container
docker compose exec backend pytest

# 5. Stop the container
docker compose down
```

### Hot Reloading
The `docker-compose.yml` configuration mounts the host project directory into the container (`./:/app`) and runs `uvicorn` with the `--reload` flag. Any code changes made locally will automatically trigger a reload inside the running container without requiring a rebuild.

---

## 4. Testing & Verification

### Swagger UI
Open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation and endpoint testing.

### Authentication
Robot-facing write endpoints require the `X-API-Key` header.
In the Swagger UI, click the **Authorize** button and enter your `.env` `API_KEY` to test these endpoints.

### Automated Tests
Run tests locally via `pytest` or inside Docker with `docker compose exec backend pytest`.

---

## 5. Running the Robot Simulator

To test the mobile app or backend logic against realistic data, you can use the built-in Hardware & Mission Simulator. This script mimics the physical `MATRIX Mini R4` by autonomously handling heartbeats, live GPS movement, and the iterative water-treatment cycle based on empirical thresholds.

```bash
# In a new terminal window (with the backend already running)
# Make sure your virtual environment is active, or use docker compose to run it
python3 scripts/simulate_robot.py
```

### What the Simulator does:
1. Pushes continuous GPS heartbeats to `/api/robot-status/{id}` and polls for dispatch commands.
2. Once you dispatch it to a waypoint (via `PATCH /api/robot-status/{id}` or the mobile app), it simulates smooth GPS navigation toward the target.
3. Upon entering the 2m boundary, it simulates the flocculation treatment cycle iteratively: taking a 'before' reading, waiting for aggregation, taking an 'after' reading with partial clarity improvements, logging treatment events, and re-treating until the water parameters fall within the target windows (Turbidity <20 NTU, pH 6.05-6.86, TDS 197-243 ppm).
4. After achieving targets (or hitting the max retries limit), it marks the waypoint as treated and returns to idle mode.

You can configure the simulation via environment variables:
- `SIM_SPEED_MS`: Simulated travel speed in meters/second (default: 5.0)
- `API_KEY`: Must match your backend `.env`
- `API_URL`: Backend URL (default: `http://localhost:8000/api`)

---

## 6. Code Conventions

- **Module Naming**: Use lowercase `snake_case` for all Python files. Pluralize router names (e.g., `sensor_readings.py`).
- **Imports**: Avoid circular dependencies. Use absolute imports (e.g., `from app.core.database import get_database`).
- **Async**: Use Motor's async `await` API. Never call synchronous blocking IO inside FastAPI route handlers.
- **Routers vs Services**: Keep routers thin. Put complex business logic, AI operations, or cross-collection aggregations into `services/`.
- **Adding a new endpoint**:
  1. Add request/response models in `app/schemas/`.
  2. Document the internal MongoDB structure in `app/models/` (if necessary for typing).
  3. Implement the route in `app/routers/`.
  4. Ensure any required server-computed fields are handled.
  5. Update `docs/api-reference.md`.
