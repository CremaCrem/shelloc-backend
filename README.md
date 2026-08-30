# SHELLOC Backend

> **S**mart **H**ydro-**E**nvironmental **L**ocator and C**l**eaner — Closed-Loop Bioremediation Backend Service

Backend API for **SHELLOC**, an autonomous water-remediation robotic vessel developed as an advanced environmental science research initiative. SHELLOC performs closed-loop **Moringa-Chitosan bio-flocculation**, **Citric Acid pH stabilization**, and **Biochar/Mesh particulate filtration** in freshwater lakes, rivers, reservoirs, and coastal perimeters.

---

## Project Overview

- **Ingests Real-Time Telemetry:** Ingests live streams (Turbidity, pH, TDS, Temperature, SONAR obstacle data, NIR floc score) from edge robotics hardware over cellular GPRS / 4G.
- **Orchestrates Closed-Loop Remediation:** Tracks the 9-state operational lifecycle (`idle` -> `navigating` -> `baseline_evaluating` -> `dispensing_flocculant` -> `incubating_15m` -> `mesh_biochar_filtering` -> `post_evaluating` -> `adaptive_stabilization` -> `completed`).
- **Broadcasts Real-Time State:** Pushes instant WebSocket updates (`/ws/robot/{id}`) for 15-minute incubation countdowns, buoyancy failsafe triggers, and live coordinates.
- **Powers Google Gemini AI:** Uses Google Gemini (`gemini-3.7-flash`) to provide non-technical operators with conversational diagnostics, remediation recommendations, and telemetry interpretation.
- **Serves Companion Clients:** Provides REST and WebSocket backends for the unified 4-view Web Portal and Mobile Application (Home, Diagnostics, AI Chat, Feedback Display).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | FastAPI (Async ASGI) |
| Database Driver | Motor (Async MongoDB) |
| Database | MongoDB Atlas / Local Replica |
| Data Validation | Pydantic v2 |
| Real-Time Comms | WebSockets (`/ws/robot/{id}`) |
| AI Engine | Google Gemini (`gemini-3.7-flash` via `google-genai` SDK) |
| Environment Config | python-dotenv |
| Server | Uvicorn with uvloop |

---

## Getting Started

### Prerequisites
- Python 3.11+
- MongoDB instance running locally (port 27017) or MongoDB Atlas URI
- Google Gemini API key (`AI_API_KEY`)

### Local Installation

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Set MONGO_URI, DB_NAME, API_KEY, AI_PROVIDER=gemini, AI_API_KEY

# 4. Launch development server
uvicorn app.main:app --reload --port 8000
```

### Accessing the API
- **Swagger Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Documentation Directory

| Document | Description |
|---|---|
| [docs/architecture.md](./docs/architecture.md) | Complete architectural blueprint, 9-state FSM, data flow, and edge responsibilities. |
| [docs/data-model.md](./docs/data-model.md) | Canonical Pydantic v2 schemas, MongoDB collections, and status matrix. |
| [docs/implementation-spec.md](./docs/implementation-spec.md) | Internal business rules, edge timer coordination, and failsafe behavior. |
| [docs/api-reference.md](./docs/api-reference.md) | Full endpoint reference, payloads, and WebSocket specifications. |
| [docs/development-guide.md](./docs/development-guide.md) | Docker workflows, simulator usage, and deployment configuration. |
