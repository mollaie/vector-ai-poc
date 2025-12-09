# Vector AI Job Matching - Architecture Documentation

## Overview

This document describes the architecture of the Vector AI Job Matching PoC, a system that uses Google Cloud's Vertex AI services to match candidates with job vacancies through semantic search and conversational AI.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Project Structure](#project-structure)
3. [Services Layer](#services-layer)
4. [ADK Integration](#adk-integration)
5. [Vertex AI Integration](#vertex-ai-integration)
6. [Data Models](#data-models)
7. [API Endpoints](#api-endpoints)
8. [Setup & Data Pipeline](#setup--data-pipeline)
9. [Running the Service](#running-the-service)
10. [Sample Data](#sample-data)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                               │
│  (REST API Calls, Interactive Docs at /docs)                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           API LAYER (FastAPI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Chat Router  │  │  Job Router  │  │Candidate Rtr│               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT LAYER (Google ADK)                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   LlmAgent (Gemini 2.5 Flash)                  │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │ │
│  │  │ search_jobs │ │ get_details │ │update_prefs │  ...tools    │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘              │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVICES LAYER                                │
│  ┌────────────┐ ┌────────────────┐ ┌────────────────┐              │
│  │JobService  │ │CandidateService│ │MatchingService │              │
│  └────────────┘ └────────────────┘ └────────────────┘              │
│  ┌────────────────┐ ┌───────────────────────┐                      │
│  │EmbeddingService│ │  VectorSearchService  │                      │
│  └────────────────┘ └───────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GOOGLE CLOUD SERVICES                             │
│  ┌────────────────┐ ┌───────────────────────┐ ┌─────────────────┐  │
│  │  Gemini 2.5    │ │  Vertex AI Embeddings │ │ Vector Search   │  │
│  │    Flash       │ │  (text-embedding-005) │ │   Index         │  │
│  └────────────────┘ └───────────────────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
vector-ai-poc/
├── config/                      # Configuration
│   ├── __init__.py
│   └── settings.py             # App settings (loads from .env)
│
├── data/                        # Runtime data (generated)
│   ├── jobs.json               # Job vacancies
│   ├── candidates.json         # Candidate profiles
│   └── job_embeddings.json     # Cached embeddings
│
├── docs/                        # Documentation
│   └── ARCHITECTURE.md         # This file
│
├── scripts/                     # Setup & data pipeline scripts
│   ├── setup_gcp.sh            # GCP project setup
│   ├── generate_data.py        # Generate mock data
│   ├── data_generator.py       # Data generation logic
│   ├── create_embeddings.py    # Create & upload embeddings
│   └── deploy_index.py         # Deploy Vector Search index
│
├── src/                         # Runtime source code
│   ├── agent/                   # ADK Agent
│   │   ├── job_agent.py        # Agent definition
│   │   └── tools.py            # Agent tool functions
│   │
│   ├── api/                     # FastAPI Application
│   │   ├── main.py             # App entry point
│   │   └── routes.py           # API endpoints
│   │
│   ├── models/                  # Data models (Pydantic)
│   │   ├── job.py              # Job model
│   │   └── candidate.py        # Candidate model
│   │
│   └── services/                # Business logic services
│       ├── job_service.py      # Job operations
│       ├── candidate_service.py # Candidate operations
│       ├── matching_service.py # Job-candidate matching
│       ├── embeddings.py       # Vertex AI embeddings
│       └── vector_search.py    # Vector Search operations
│
├── tests/                       # Test files
├── .env                         # Environment variables (not in git)
├── requirements.txt             # Dependencies
└── README.md                    # Quick start guide
```

### Separation of Concerns

| Directory | Purpose | When Used |
|-----------|---------|-----------|
| `scripts/` | Data generation, setup, deployment | One-time setup |
| `src/` | Runtime application code | Every request |
| `config/` | Configuration management | Both |
| `data/` | Generated data files | Runtime |
| `docs/` | Documentation | Reference |

---

## Services Layer

The services layer follows **SOLID principles** and provides clean separation of concerns.

### JobService (`src/services/job_service.py`)

**Responsibility:** Manage job data and operations.

```python
from src.services import get_job_service

job_service = get_job_service()

# Get a job by ID
job = job_service.get_job("job-001")

# Get all jobs with pagination
jobs = job_service.get_jobs_paginated(offset=0, limit=20)

# Format job for display
formatted = job_service.format_job_for_display(job, include_match_score=True, match_score=0.85)
```

### CandidateService (`src/services/candidate_service.py`)

**Responsibility:** Manage candidate data, preferences, and job interactions.

```python
from src.services import get_candidate_service

candidate_service = get_candidate_service()

# Get candidate profile
candidate = candidate_service.get_candidate("candidate-001")

# Update preferences
success, fields = candidate_service.update_preferences(
    candidate_id="candidate-001",
    min_salary=180000,
    preferred_location_types=["remote"]
)

# Record job acceptance/decline
candidate_service.accept_job("candidate-001", "job-042")
candidate_service.decline_jobs("candidate-001", ["job-001", "job-002"])
```

### MatchingService (`src/services/matching_service.py`)

**Responsibility:** Match candidates with jobs using vector search or fallback.

```python
from src.services import get_matching_service

matching_service = get_matching_service()

# Search jobs for a candidate
results = matching_service.search_jobs_for_candidate(
    candidate_id="candidate-001",
    additional_criteria="remote only",
    num_results=3
)

# Search jobs by text query
results = matching_service.search_jobs_by_text(
    query="python developer",
    num_results=10
)
```

### EmbeddingService (`src/services/embeddings.py`)

**Responsibility:** Generate text embeddings using Vertex AI.

```python
from src.services import get_embedding_service

embedding_service = get_embedding_service()

# Generate embedding for a document
embedding = embedding_service.get_document_embedding("Job description text...")

# Generate embedding for a search query
query_embedding = embedding_service.get_query_embedding("python developer remote")
```

### VectorSearchService (`src/services/vector_search.py`)

**Responsibility:** Perform vector similarity search using Vertex AI Vector Search.

```python
from src.services import get_vector_search_service

vector_service = get_vector_search_service()

# Search by text (generates embedding internally)
results = vector_service.search_by_text("data scientist", num_neighbors=5)

# Search by embedding vector
results = vector_service.search(query_embedding=embedding, num_neighbors=5)
```

---

## ADK Integration

### Agent Definition (`src/agent/job_agent.py`)

The agent uses **Google ADK (Agent Development Kit)** with **Gemini 2.5 Flash**.

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

agent = LlmAgent(
    model="gemini-2.5-flash",
    name="job_matching_agent",
    instruction=AGENT_INSTRUCTION,  # System prompt
    tools=[
        FunctionTool(func=search_jobs),
        FunctionTool(func=get_job_details),
        FunctionTool(func=update_candidate_preferences),
        # ... more tools
    ]
)
```

### Agent Tools (`src/agent/tools.py`)

Tools are thin wrappers that the agent calls to perform actions:

| Tool | Purpose |
|------|---------|
| `search_jobs` | Find matching jobs for a candidate |
| `get_job_details` | Get full details of a specific job |
| `update_candidate_preferences` | Update salary, location, industry preferences |
| `accept_job` | Record job acceptance |
| `decline_jobs` | Record declined jobs |
| `get_candidate_profile` | Retrieve candidate information |
| `list_available_candidates` | List all candidates (for testing) |

### Session Management

Sessions are managed using ADK's `InMemorySessionService`:

```python
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

session_service = InMemorySessionService()

runner = Runner(
    agent=agent,
    app_name="job_matching_app",
    session_service=session_service
)

# Run agent with session continuity
async for event in runner.run_async(
    user_id="candidate-001",
    session_id="session-uuid",
    new_message=message
):
    # Process response
```

---

## Vertex AI Integration

### Models Used

| Model | Purpose | Dimensions |
|-------|---------|------------|
| `gemini-2.5-flash` | Conversational AI agent | N/A |
| `text-embedding-005` | Text embeddings | 768 |

### Vector Search Index

The Vector Search index uses:
- **Algorithm:** Tree-AH (Approximate Nearest Neighbor)
- **Distance Metric:** Cosine Distance
- **Update Method:** Stream Update
- **Machine Type:** e2-standard-16

### Configuration

Environment variables (`.env`):

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1
GCS_BUCKET=your-bucket-name
EMBEDDING_MODEL=text-embedding-005
GEMINI_MODEL=gemini-2.5-flash
VECTOR_SEARCH_INDEX_ID=projects/.../indexes/...
VECTOR_SEARCH_ENDPOINT_ID=projects/.../indexEndpoints/...
```

---

## Data Models

### Job Model (`src/models/job.py`)

```python
class Job(BaseModel):
    id: str
    title: str
    company: str
    description: str
    required_skills: list[str]
    preferred_skills: list[str]
    experience_level: ExperienceLevel  # junior/mid/senior/lead/principal
    min_years_experience: int
    location_type: LocationType  # remote/hybrid/onsite
    location: Optional[str]
    salary_min: int
    salary_max: int
    industry: str
    department: str
    benefits: list[str]
```

### Candidate Model (`src/models/candidate.py`)

```python
class Candidate(BaseModel):
    id: str
    name: str
    email: str
    summary: str
    skills: list[str]
    years_experience: int
    current_title: str
    preferred_titles: list[str]
    preferred_location_types: list[LocationType]
    preferred_locations: list[str]
    min_salary: int
    max_salary: int
    preferred_industries: list[str]
    declined_job_ids: list[str]
    accepted_job_id: Optional[str]
```

---

## API Endpoints

### Chat (Agent Interaction)

```bash
POST /api/chat
{
    "message": "Find me jobs matching my profile",
    "candidate_id": "candidate-001",
    "session_id": "optional-session-id"
}
```

### Jobs

```bash
GET  /api/jobs                    # List jobs (paginated)
GET  /api/jobs/{job_id}           # Get job details
GET  /api/jobs/search/text?query= # Semantic search
```

### Candidates

```bash
GET   /api/candidates             # List all candidates
GET   /api/candidates/{id}        # Get candidate details
POST  /api/candidates             # Create candidate
PATCH /api/candidates/{id}        # Update candidate
```

### Sessions

```bash
POST /api/sessions                # Create session
GET  /api/sessions/{id}           # Get session info
GET  /api/sessions/{id}/history   # Get chat history
```

---

## Setup & Data Pipeline

### 1. GCP Setup (One-time)

```bash
./scripts/setup_gcp.sh YOUR_PROJECT_ID us-central1
```

Creates:
- GCS bucket for embeddings
- Enables required APIs
- Creates `.env` file

### 2. Generate Data

```bash
python scripts/generate_data.py
```

Generates:
- 100 tech jobs + 200 blue-collar jobs (300 total)
- 10 tech candidates + 20 blue-collar candidates (30 total)

### 3. Create Embeddings

```bash
python scripts/create_embeddings.py
```

- Generates 768-dim embeddings for all jobs
- Uploads to GCS in JSONL format

### 4. Deploy Vector Search

```bash
python scripts/deploy_index.py
```

- Creates Vector Search index (~30-60 min)
- Creates endpoint
- Deploys index to endpoint (~20-30 min)

---

## Running the Service

### Start the API

```bash
# Activate virtual environment
source venv/bin/activate

# Start the server
python -m src.api.main
```

The API runs at `http://localhost:8000`

### Interactive Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Health Check

```bash
curl http://localhost:8000/health
```

---

## Sample Data

### Tech Candidates (IDs: candidate-001 to candidate-010)

| ID | Name | Title | Experience |
|----|------|-------|------------|
| candidate-001 | Avery Rodriguez | Senior Data Scientist | 9 years |
| candidate-002 | Blake Williams | Staff Engineer | 11 years |
| candidate-003 | Avery Chen | Full Stack Developer | 11 years |

### Blue-Collar Candidates (IDs: candidate-bc-001 to candidate-bc-020)

| ID | Name | Title | Hourly Rate |
|----|------|-------|-------------|
| candidate-bc-001 | Mike Thomas | General Laborer | ~$24/hr |
| candidate-bc-009 | Linda Brown | Route Driver (CDL) | ~$24/hr |
| candidate-bc-011 | Chris Jackson | Delivery Driver | ~$19/hr |

### Job Types

**Tech Jobs (IDs: job-001 to job-100):**
- Software Engineer, Data Scientist, DevOps Engineer
- Salary: $70,000 - $280,000/year

**Blue-Collar Jobs (IDs: job-bc-001 to job-bc-200):**
- Delivery Driver, Warehouse Associate, Security Guard
- Pay: $12-30/hour, $100-240/day, $500-1200/week

### Example API Calls

```bash
# Chat with tech candidate
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find me senior engineering jobs", "candidate_id": "candidate-001"}'

# Chat with blue-collar candidate
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need a delivery driver job", "candidate_id": "candidate-bc-011"}'

# Search jobs
curl "http://localhost:8000/api/jobs/search/text?query=forklift%20warehouse&limit=5"
```

---

## Design Principles Applied

### SOLID Principles

1. **Single Responsibility (SRP):** Each service handles one domain
2. **Open/Closed (OCP):** Services can be extended without modification
3. **Liskov Substitution (LSP):** Services can be swapped via dependency injection
4. **Interface Segregation (ISP):** Small, focused interfaces
5. **Dependency Inversion (DIP):** High-level modules depend on abstractions

### Clean Architecture

- **Separation of Concerns:** Scripts vs Runtime code
- **Dependency Injection:** Services injected into tools and routes
- **Layered Architecture:** API → Agent → Services → External Services

---

## Error Handling

| Error | HTTP Code | Description |
|-------|-----------|-------------|
| Candidate not found | 404 | Invalid candidate_id |
| Job not found | 404 | Invalid job_id |
| Vector search unavailable | 503 | Index not deployed |
| Agent error | 500 | LLM or tool failure |

---

## Monitoring

### GCP Console Links

- **Vector Search Indexes:** `console.cloud.google.com/vertex-ai/matching-engine/indexes`
- **Vector Search Endpoints:** `console.cloud.google.com/vertex-ai/matching-engine/index-endpoints`
- **Cloud Storage:** `console.cloud.google.com/storage/browser`

---

*Last updated: December 2024*

