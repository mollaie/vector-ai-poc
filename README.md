# Vector AI Job Matching PoC

A proof-of-concept job matching system using Google Cloud's AI services:

- **Google ADK** (Agent Development Kit) for conversational AI
- **Vertex AI** for text embeddings (text-embedding-005)
- **Vertex AI Vector Search** for semantic job matching
- **Gemini 2.5 Flash** for natural language understanding

## Quick Start

### Prerequisites

- Python 3.10+
- Google Cloud account with billing enabled
- `gcloud` CLI installed

### 1. Setup Environment

```bash
# Clone and navigate to project
cd vector-ai-poc

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Google Cloud

```bash
# Run setup script (creates .env file)
./scripts/setup_gcp.sh YOUR_PROJECT_ID us-central1

# Or configure manually
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### 3. Generate Data & Deploy

```bash
# Generate mock data (300 jobs, 30 candidates)
python scripts/generate_data.py

# Create embeddings
python scripts/create_embeddings.py

# Deploy Vector Search index (takes ~1 hour)
python scripts/deploy_index.py
```

### 4. Start the API

```bash
python -m src.api.main
```

API runs at `http://localhost:8000`

## Usage Examples

### Chat with AI Agent

```bash
# Tech candidate looking for jobs
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find me senior engineering jobs", "candidate_id": "candidate-001"}'

# Blue-collar candidate
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need a delivery driver job", "candidate_id": "candidate-bc-011"}'

# Update preferences through chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need at least $180,000 salary", "candidate_id": "candidate-001"}'
```

### Search Jobs Directly

```bash
# Semantic search
curl "http://localhost:8000/api/jobs/search/text?query=python%20developer&limit=5"

# Search warehouse jobs
curl "http://localhost:8000/api/jobs/search/text?query=forklift%20warehouse&limit=5"
```

### API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Project Structure

```
vector-ai-poc/
├── scripts/           # Setup & data generation (one-time use)
│   ├── setup_gcp.sh
│   ├── generate_data.py
│   ├── create_embeddings.py
│   └── deploy_index.py
│
├── src/               # Runtime application code
│   ├── agent/         # ADK Agent & tools
│   ├── api/           # FastAPI routes
│   ├── models/        # Data models
│   └── services/      # Business logic
│
├── config/            # Configuration
├── data/              # Generated data files
└── docs/              # Documentation
```

## Data Overview

| Category | Jobs | Candidates |
|----------|------|------------|
| Tech | 100 | 10 |
| Blue-collar | 200 | 20 |
| **Total** | **300** | **30** |

### Sample Candidate IDs

**Tech Candidates:**
- `candidate-001` - Avery Rodriguez (Senior Data Scientist)
- `candidate-002` - Blake Williams (Staff Engineer)

**Blue-collar Candidates:**
- `candidate-bc-001` - Mike Thomas (General Laborer)
- `candidate-bc-011` - Chris Jackson (Delivery Driver)
- `candidate-bc-009` - Linda Brown (Route Driver with CDL)

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed documentation including:
- System architecture diagrams
- Service descriptions
- ADK & Vertex AI integration details
- API reference
- Design principles (SOLID, Clean Architecture)

## Environment Variables

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1
GCS_BUCKET=your-bucket-name

# Models
EMBEDDING_MODEL=text-embedding-005
GEMINI_MODEL=gemini-2.5-flash

# Vector Search (set after deployment)
VECTOR_SEARCH_INDEX_ID=projects/.../indexes/...
VECTOR_SEARCH_ENDPOINT_ID=projects/.../indexEndpoints/...
```

## Estimated Costs

| Resource | Cost |
|----------|------|
| Index storage | ~$0.20/GB/month |
| Index endpoint | ~$0.10/hour |
| Queries | ~$0.0001/query |
| Embeddings | ~$0.025/1K chars |

**Estimated monthly cost for PoC:** $5-15/month

## License

MIT License
