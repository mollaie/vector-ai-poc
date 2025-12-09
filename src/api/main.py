"""FastAPI application entry point."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config.settings import get_settings
from src.api.routes import (
    chat_router,
    candidates_router,
    jobs_router,
    sessions_router,
    perf_router,
)

# Create FastAPI app
app = FastAPI(
    title="Vector AI Job Matching PoC",
    description="""
    A proof-of-concept job matching system using:
    - Google ADK for agentic interactions
    - Vertex AI for text embeddings
    - Vertex AI Vector Search for semantic job matching
    - Gemini for natural language understanding
    
    ## Features
    - Chat with an AI agent to find matching jobs
    - Update preferences through natural conversation
    - Accept or decline job offers
    - Automatic re-matching after preference updates
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api")
app.include_router(candidates_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(perf_router, prefix="/api")

# Mount static files
static_path = project_root / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Vector AI Job Matching PoC",
        "version": "0.1.0",
        "docs": "/docs",
        "chat_ui": "/chat",
        "endpoints": {
            "chat": "/api/chat",
            "chat_stream": "/api/chat/stream",
            "candidates": "/api/candidates",
            "jobs": "/api/jobs",
            "sessions": "/api/sessions",
            "performance": "/api/perf/stats",
        }
    }


@app.get("/chat")
async def chat_ui():
    """Serve the chat UI."""
    chat_html = project_root / "static" / "chat.html"
    if chat_html.exists():
        return FileResponse(str(chat_html))
    return {"error": "Chat UI not found"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "project": settings.google_cloud_project or "not configured",
        "region": settings.google_cloud_region,
        "models": {
            "embedding": settings.embedding_model,
            "gemini": settings.gemini_model
        }
    }


def main():
    """Run the application with uvicorn."""
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()

