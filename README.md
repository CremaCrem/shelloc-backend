# SHELLOC Backend

> **S**mart **H**ydro-**E**nvironmental **L**ocator and C**l**eaner — Backend Service

Backend API for **SHELLOC**, an autonomous water-remediation robot developed as a school research project at Bicol Regional Science High School, Region V (Bicol), Philippines. SHELLOC performs Moringa-Chitosan flocculation and filtration of suspended particulate matter (SPM) in rivers, lakes, reservoirs, and coastal waters.

---

## Project Overview

- **Receives** real-time sensor data (turbidity, pH, TDS, NIR floc score) from the robot over GPRS
- **Receives** treatment event logs (flocculant dosage, floc aggregation timing, outcomes)
- **Serves** all collected data to a React Native Expo companion mobile app
- **Powers** an AI chat feature that interprets water quality data for non-technical users

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI (async) |
| Database driver | Motor (async MongoDB) |
| Database | MongoDB (local dev → Atlas for deployment) |
| Data validation | Pydantic v2 |
| Environment config | python-dotenv |
| AI providers | OpenAI / Claude / Gemini (configurable via `.env`) |
| Server | Uvicorn with uvloop |

---

## Getting Started

### Prerequisites
- Python 3.11+
- MongoDB running locally on port 27017
- An AI provider API key (OpenAI, Claude, or Gemini)

### Local Installation

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your specific values

# 4. Run the development server
uvicorn app.main:app --reload --port 8000
```

### Accessing the API
Open [http://localhost:8000/docs](http://localhost:8000/docs) to access the interactive Swagger UI.

Robot-facing write endpoints require an `X-API-Key` header matching the `API_KEY` defined in `.env`.

---

## Documentation Directory

The project documentation is organized in the `docs/` folder:

| Document | Purpose |
|---|---|
| [docs/architecture.md](./docs/architecture.md) | How the system is organized, components, and data flow. |
| [docs/api-reference.md](./docs/api-reference.md) | Complete endpoint listing, HTTP methods, and auth requirements. |
| [docs/data-model.md](./docs/data-model.md) | Canonical data reference, Pydantic schemas, and MongoDB structure. |
| [docs/implementation-spec.md](./docs/implementation-spec.md) | Backend behaviors, business rules, computed fields, and validation logic. |
| [docs/development-guide.md](./docs/development-guide.md) | Local setup, testing, and contribution conventions. |

For AI coding agents and IDEs, see [AGENTS.md](./AGENTS.md).
