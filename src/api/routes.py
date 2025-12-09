"""FastAPI route definitions."""

import json
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agent.job_agent import get_job_matching_agent
from src.services import (
    get_job_service,
    get_candidate_service,
    get_matching_service,
)
from src.models.job import JobResponse
from src.models.candidate import (
    Candidate,
    CandidateCreate,
    CandidateUpdate,
    CandidateResponse,
)


# Routers
chat_router = APIRouter(prefix="/chat", tags=["Chat"])
candidates_router = APIRouter(prefix="/candidates", tags=["Candidates"])
jobs_router = APIRouter(prefix="/jobs", tags=["Jobs"])
sessions_router = APIRouter(prefix="/sessions", tags=["Sessions"])


# Session management
session_service = InMemorySessionService()
_sessions: dict[str, dict] = {}


# Request/Response models
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message to the agent")
    candidate_id: str = Field(..., description="ID of the candidate chatting")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    session_id: str
    response: str
    timestamp: str


class SessionCreate(BaseModel):
    """Request model for creating a new session."""
    candidate_id: str


class SessionResponse(BaseModel):
    """Response model for session."""
    session_id: str
    candidate_id: str
    created_at: str
    message_count: int


class MessageHistory(BaseModel):
    """Model for message history."""
    role: str
    content: str
    timestamp: str


class SessionHistoryResponse(BaseModel):
    """Response model for session history."""
    session_id: str
    candidate_id: str
    messages: list[MessageHistory]


# Chat endpoints
@chat_router.post("", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """Send a message to the job matching agent.
    
    The agent will:
    - Search for matching jobs based on candidate profile
    - Provide job details on request
    - Update candidate preferences
    - Record job acceptances/declines
    """
    # Get or create session
    session_id = request.session_id
    if not session_id or session_id not in _sessions:
        session_id = str(uuid.uuid4())
        _sessions[session_id] = {
            "candidate_id": request.candidate_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": []
        }
    
    # Verify candidate exists
    candidate_service = get_candidate_service()
    if not candidate_service.candidate_exists(request.candidate_id):
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {request.candidate_id} not found"
        )
    
    # Get the agent
    agent = get_job_matching_agent()
    
    # Create runner for this interaction
    APP_NAME = "job_matching_app"
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    
    # Ensure session exists in session service
    existing_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=request.candidate_id,
        session_id=session_id
    )
    if not existing_session:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=request.candidate_id,
            session_id=session_id
        )
    
    # Add context about the candidate to the message
    context_message = f"[Candidate ID: {request.candidate_id}] {request.message}"
    
    # Store user message in history
    _sessions[session_id]["messages"].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    try:
        # Run the agent
        response_text = ""
        async for event in runner.run_async(
            user_id=request.candidate_id,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=context_message)]
            )
        ):
            # Collect the response text
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text += part.text
        
        # Store assistant response in history
        _sessions[session_id]["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return ChatResponse(
            session_id=session_id,
            response=response_text,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


# Session endpoints
@sessions_router.post("", response_model=SessionResponse)
async def create_session(request: SessionCreate) -> SessionResponse:
    """Create a new chat session for a candidate."""
    # Verify candidate exists
    candidate_service = get_candidate_service()
    if not candidate_service.candidate_exists(request.candidate_id):
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {request.candidate_id} not found"
        )
    
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "candidate_id": request.candidate_id,
        "created_at": datetime.utcnow().isoformat(),
        "messages": []
    }
    
    return SessionResponse(
        session_id=session_id,
        candidate_id=request.candidate_id,
        created_at=_sessions[session_id]["created_at"],
        message_count=0
    )


@sessions_router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get session information."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    return SessionResponse(
        session_id=session_id,
        candidate_id=session["candidate_id"],
        created_at=session["created_at"],
        message_count=len(session["messages"])
    )


@sessions_router.get("/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str) -> SessionHistoryResponse:
    """Get the message history for a session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    return SessionHistoryResponse(
        session_id=session_id,
        candidate_id=session["candidate_id"],
        messages=[
            MessageHistory(**msg) for msg in session["messages"]
        ]
    )


# Candidate endpoints
@candidates_router.get("", response_model=list[CandidateResponse])
async def list_candidates() -> list[CandidateResponse]:
    """List all candidates."""
    candidate_service = get_candidate_service()
    candidates = candidate_service.get_all_candidates()
    return [CandidateResponse.from_candidate(c) for c in candidates]


@candidates_router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(candidate_id: str) -> CandidateResponse:
    """Get a candidate by ID."""
    candidate_service = get_candidate_service()
    candidate = candidate_service.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateResponse.from_candidate(candidate)


@candidates_router.post("", response_model=CandidateResponse)
async def create_candidate(candidate_data: CandidateCreate) -> CandidateResponse:
    """Create a new candidate."""
    candidate_service = get_candidate_service()
    
    # Generate ID
    candidate_id = f"candidate-{uuid.uuid4().hex[:8]}"
    
    candidate = Candidate(
        id=candidate_id,
        **candidate_data.model_dump()
    )
    
    candidate_service.update_candidate(candidate)
    
    return CandidateResponse.from_candidate(candidate)


@candidates_router.patch("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    updates: CandidateUpdate
) -> CandidateResponse:
    """Update a candidate's profile."""
    candidate_service = get_candidate_service()
    candidate = candidate_service.get_candidate(candidate_id)
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(candidate, field, value)
    
    candidate_service.update_candidate(candidate)
    
    return CandidateResponse.from_candidate(candidate)


# Job endpoints
@jobs_router.get("", response_model=list[JobResponse])
async def list_jobs(
    limit: int = 20,
    offset: int = 0
) -> list[JobResponse]:
    """List all jobs with pagination."""
    job_service = get_job_service()
    job_list = job_service.get_jobs_paginated(offset=offset, limit=limit)
    return [JobResponse.from_job(j) for j in job_list]


@jobs_router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Get a job by ID."""
    job_service = get_job_service()
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_job(job)


@jobs_router.get("/search/text")
async def search_jobs_by_text(
    query: str,
    limit: int = 10
) -> dict:
    """Search jobs by text query using vector search."""
    matching_service = get_matching_service()
    result = matching_service.search_jobs_by_text(query=query, num_results=limit)
    
    if "error" in result and not result.get("results"):
        raise HTTPException(
            status_code=503,
            detail=f"Vector search not available: {result['error']}"
        )
    
    return result

