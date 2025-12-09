"""FastAPI route definitions."""

import json
import uuid
import time
import asyncio
from typing import Optional, AsyncGenerator
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
from src.services.cache_service import get_cache_service, candidate_cache_key
from src.services.async_embedding_service import get_async_embedding_service
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
# ADK session service - shared instance for state management
# According to https://cloud.google.com/blog/topics/developers-practitioners/remember-this-agent-state-and-memory-with-adk
# Session STATE is lightweight (key-value scratchpad), EVENT HISTORY causes slowdowns
session_service = InMemorySessionService()
_sessions: dict[str, dict] = {}  # Our history tracking (for display)
_candidate_sessions: dict[str, str] = {}  # candidate_id -> active session_id


def get_or_create_session(candidate_id: str, session_id: Optional[str] = None) -> str:
    """Get existing session or create new one for a candidate.
    
    Logic:
    1. If session_id provided and valid -> use it
    2. If candidate has an active session -> reuse it
    3. Otherwise -> create new session
    
    Args:
        candidate_id: The candidate ID
        session_id: Optional session ID from request
        
    Returns:
        Session ID to use
    """
    # Case 1: Valid session_id provided
    if session_id and session_id in _sessions:
        # Verify it belongs to this candidate
        if _sessions[session_id]["candidate_id"] == candidate_id:
            return session_id
    
    # Case 2: Check if candidate has an active session
    if candidate_id in _candidate_sessions:
        existing_session_id = _candidate_sessions[candidate_id]
        if existing_session_id in _sessions:
            return existing_session_id
    
    # Case 3: Create new session
    new_session_id = str(uuid.uuid4())
    _sessions[new_session_id] = {
        "candidate_id": candidate_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],
        "preferences": {}  # Track stated preferences across conversation
    }
    _candidate_sessions[candidate_id] = new_session_id
    
    return new_session_id


def build_conversation_context(session_id: str, current_message: str, candidate_id: str, max_history: int = 6) -> str:
    """Build context message including conversation history and stated preferences.
    
    This ensures the LLM knows what was discussed previously in this session.
    
    Args:
        session_id: The session ID
        current_message: The current user message
        candidate_id: The candidate ID
        max_history: Maximum number of previous messages to include (default 6 = 3 turns)
        
    Returns:
        Context message with history and preferences
    """
    session = _sessions.get(session_id, {})
    messages = session.get("messages", [])
    preferences = session.get("preferences", {})
    
    context_parts = []
    
    # Add candidate ID
    context_parts.append(f"[Candidate ID: {candidate_id}]")
    
    # Add stated preferences if any (persistent across conversation)
    if preferences:
        pref_str = ", ".join([f"{k}: {v}" for k, v in preferences.items()])
        context_parts.append(f"[Stated Preferences: {pref_str}]")
    
    # Add recent conversation history
    if messages:
        recent_messages = messages[-max_history:]  # Last N messages
        if recent_messages:
            context_parts.append("\n[Recent Conversation:]")
            for msg in recent_messages:
                role = "User" if msg["role"] == "user" else "Assistant"
                # Truncate long messages to keep context manageable
                content = msg["content"][:500] + "..." if len(msg["content"]) > 500 else msg["content"]
                context_parts.append(f"{role}: {content}")
            context_parts.append("[End of History]")
    
    # Add current message
    context_parts.append(f"\n[Current Message]: {current_message}")
    
    return "\n".join(context_parts)


def extract_preferences_from_message(message: str, current_preferences: dict) -> tuple[dict, dict]:
    """Extract stated preferences from user message to track across conversation.
    
    This is a simple keyword extraction - the LLM will do the real understanding.
    We track what the user has mentioned and return changes for persistence.
    
    Args:
        message: The user's message
        current_preferences: Current tracked preferences
        
    Returns:
        Tuple of (updated_preferences, changes_to_persist)
        - updated_preferences: Full preferences dict for session
        - changes_to_persist: Only the new/changed values to save to profile
    """
    import re
    message_lower = message.lower()
    updated = current_preferences.copy()
    changes = {}  # Track what actually changed for persistence
    
    # Salary mentions
    salary_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*|\d+)(?:k)?(?:\s*(?:salary|minimum|min|at least))?', message_lower)
    if salary_match and any(word in message_lower for word in ['salary', 'minimum', 'min', 'at least', 'want', 'need', 'looking for']):
        salary_str = salary_match.group(1).replace(',', '')
        try:
            salary = int(salary_str)
            if salary < 1000:  # Likely in thousands
                salary *= 1000
            if updated.get("min_salary") != salary:
                updated["min_salary"] = salary
                changes["min_salary"] = salary
        except ValueError:
            pass
    
    # Location preferences (must match LocationType enum values: "remote", "hybrid", "onsite")
    new_location = None
    if 'remote' in message_lower and 'not remote' not in message_lower:
        new_location = "remote"
    elif 'hybrid' in message_lower:
        new_location = "hybrid"
    elif 'onsite' in message_lower or 'on-site' in message_lower or 'in-person' in message_lower:
        new_location = "onsite"
    
    if new_location and updated.get("location") != new_location:
        updated["location"] = new_location
        changes["preferred_location_types"] = [new_location]
    
    # Job type/title mentions - map to actual job titles
    job_title_map = {
        'driver': ['Driver', 'Delivery Driver'],
        'delivery': ['Delivery Driver', 'Courier'],
        'warehouse': ['Warehouse Associate', 'Warehouse Loader'],
        'security': ['Security Guard', 'Security Officer'],
        'technician': ['Technician', 'Maintenance Technician'],
        'handyman': ['Handyman', 'Maintenance Worker'],
        'cleaner': ['Cleaner', 'Janitor'],
        'engineer': ['Engineer', 'Software Engineer'],
        'developer': ['Developer', 'Software Developer'],
        'manager': ['Manager', 'Project Manager'],
        'analyst': ['Analyst', 'Data Analyst'],
        'designer': ['Designer', 'UI Designer'],
    }
    
    for keyword, titles in job_title_map.items():
        if keyword in message_lower:
            if updated.get("job_interest") != keyword:
                updated["job_interest"] = keyword
                changes["preferred_titles"] = titles
            break
    
    # Certifications/skills mentioned
    if 'license' in message_lower or 'driving license' in message_lower:
        has_license = "yes" if any(w in message_lower for w in ['have', 'yes', 'got', 'i do']) else "mentioned"
        updated["has_license"] = has_license
        # If they confirm they have a license, add it as a skill
        if has_license == "yes":
            changes["add_skill"] = "Valid Driver's License"
    
    # Industry preferences
    industry_keywords = {
        'tech': 'Technology',
        'healthcare': 'Healthcare',
        'finance': 'Finance',
        'retail': 'Retail',
        'logistics': 'Logistics',
        'transportation': 'Transportation',
        'manufacturing': 'Manufacturing',
    }
    for keyword, industry in industry_keywords.items():
        if keyword in message_lower:
            if updated.get("industry") != industry:
                updated["industry"] = industry
                changes["preferred_industries"] = [industry]
            break
    
    return updated, changes


def persist_preference_changes(candidate_id: str, changes: dict) -> bool:
    """Persist extracted preference changes to the candidate profile.
    
    This ensures that preferences mentioned in conversation are saved
    so they persist across sessions and service restarts.
    
    Args:
        candidate_id: The candidate to update
        changes: Dictionary of changes to persist
        
    Returns:
        True if changes were made, False otherwise
    """
    if not changes:
        return False
    
    candidate_service = get_candidate_service()
    candidate = candidate_service.get_candidate(candidate_id)
    if not candidate:
        return False
    
    made_changes = False
    
    # Update min_salary
    if "min_salary" in changes:
        candidate.min_salary = changes["min_salary"]
        made_changes = True
    
    # Update preferred location types
    if "preferred_location_types" in changes:
        from src.models.job import LocationType
        try:
            candidate.preferred_location_types = [
                LocationType(lt) for lt in changes["preferred_location_types"]
            ]
            made_changes = True
        except ValueError:
            pass  # Invalid location type, skip
    
    # Update preferred titles
    if "preferred_titles" in changes:
        # Merge with existing, don't replace entirely
        existing_titles = set(candidate.preferred_titles or [])
        new_titles = set(changes["preferred_titles"])
        candidate.preferred_titles = list(existing_titles | new_titles)
        made_changes = True
    
    # Update preferred industries
    if "preferred_industries" in changes:
        existing = set(candidate.preferred_industries or [])
        new_industries = set(changes["preferred_industries"])
        candidate.preferred_industries = list(existing | new_industries)
        made_changes = True
    
    # Add skill (like driver's license)
    if "add_skill" in changes:
        if changes["add_skill"] not in candidate.skills:
            candidate.skills.append(changes["add_skill"])
            made_changes = True
    
    # Save if we made any changes
    if made_changes:
        candidate_service.update_candidate(candidate)
    
    return made_changes


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
    
    Sessions are automatically reused for the same candidate.
    Conversation history is maintained and sent to the LLM for context.
    """
    # Verify candidate exists first
    candidate_service = get_candidate_service()
    if not candidate_service.candidate_exists(request.candidate_id):
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {request.candidate_id} not found"
        )
    
    # Get or create our display session (for history tracking)
    display_session_id = get_or_create_session(request.candidate_id, request.session_id)
    
    # Extract and track preferences from user message
    current_prefs = _sessions[display_session_id].get("preferences", {})
    updated_prefs, changes_to_persist = extract_preferences_from_message(request.message, current_prefs)
    _sessions[display_session_id]["preferences"] = updated_prefs
    
    # PERSIST preference changes to candidate profile (survives restarts!)
    if changes_to_persist:
        persist_preference_changes(request.candidate_id, changes_to_persist)
    
    # Store user message in our history tracking BEFORE building context
    _sessions[display_session_id]["messages"].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Build context with conversation history (excluding the message we just added)
    # We want history BEFORE current message, then current message
    temp_messages = _sessions[display_session_id]["messages"][:-1]  # Exclude current
    _sessions[display_session_id]["messages"] = temp_messages
    context_message = build_conversation_context(
        display_session_id, 
        request.message, 
        request.candidate_id,
        max_history=8  # Include up to 8 previous messages (4 turns)
    )
    # Restore message list
    _sessions[display_session_id]["messages"].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Get the agent
    agent = get_job_matching_agent()
    
    # Use unique interaction ID to avoid ADK event history accumulation
    # This keeps each LLM call independent while context is passed via message
    interaction_id = f"{display_session_id}-{uuid.uuid4().hex[:8]}"
    
    APP_NAME = "job_matching_app"
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    
    # Create new ADK session for this interaction (prevents history buildup)
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=request.candidate_id,
        session_id=interaction_id
    )
    
    try:
        # Run the agent with conversation context included in the message
        response_text = ""
        async for event in runner.run_async(
            user_id=request.candidate_id,
            session_id=interaction_id,
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
        
        # Store assistant response in our history
        _sessions[display_session_id]["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Return display_session_id (consistent for candidate)
        return ChatResponse(
            session_id=display_session_id,
            response=response_text,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@chat_router.post("/stream")
async def chat_with_agent_stream(request: ChatRequest) -> StreamingResponse:
    """Stream chat responses for real-time interaction.
    
    Returns Server-Sent Events (SSE) stream with the following event types:
    - data: Text chunks as they're generated
    - done: Final message with session info
    - error: Error message if something goes wrong
    
    This endpoint provides much faster perceived response time
    as users see text appearing immediately.
    
    Sessions are automatically reused for the same candidate.
    Conversation history is maintained and sent to the LLM for context.
    """
    async def generate() -> AsyncGenerator[str, None]:
        start_time = time.time()
        
        # Verify candidate exists (use cache)
        cache = get_cache_service()
        cache_key = candidate_cache_key(request.candidate_id)
        candidate_exists = cache.get(cache_key)
        
        if candidate_exists is None:
            candidate_service = get_candidate_service()
            candidate_exists = candidate_service.candidate_exists(request.candidate_id)
            cache.set(cache_key, candidate_exists, ttl=60)  # Cache for 1 minute
        
        if not candidate_exists:
            yield f"data: {json.dumps({'error': f'Candidate {request.candidate_id} not found'})}\n\n"
            return
        
        # Get or create session (reuses existing session for same candidate)
        session_id = get_or_create_session(request.candidate_id, request.session_id)
        
        # Extract and track preferences from user message
        current_prefs = _sessions[session_id].get("preferences", {})
        updated_prefs, changes_to_persist = extract_preferences_from_message(request.message, current_prefs)
        _sessions[session_id]["preferences"] = updated_prefs
        
        # PERSIST preference changes to candidate profile (survives restarts!)
        if changes_to_persist:
            persist_preference_changes(request.candidate_id, changes_to_persist)
        
        # Build context with conversation history BEFORE adding current message
        context_message = build_conversation_context(
            session_id, 
            request.message, 
            request.candidate_id,
            max_history=8  # Include up to 8 previous messages (4 turns)
        )
        
        # Store user message AFTER building context
        _sessions[session_id]["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Get the agent
        agent = get_job_matching_agent()
        
        # Use unique interaction ID to avoid ADK event history accumulation
        interaction_id = f"{session_id}-{uuid.uuid4().hex[:8]}"
        
        APP_NAME = "job_matching_app"
        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=session_service,
        )
        
        # Create new ADK session for this interaction (prevents history buildup)
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=request.candidate_id,
            session_id=interaction_id
        )
        
        # Send session info first (use display session_id for user)
        yield f"data: {json.dumps({'session_id': session_id, 'type': 'start'})}\n\n"
        
        try:
            response_text = ""
            chunk_count = 0
            
            # Use interaction_id for ADK runner (prevents history buildup)
            # Context message includes conversation history
            async for event in runner.run_async(
                user_id=request.candidate_id,
                session_id=interaction_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text=context_message)]
                )
            ):
                if hasattr(event, 'content') and event.content:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            chunk = part.text
                            response_text += chunk
                            chunk_count += 1
                            # Stream each chunk
                            yield f"data: {json.dumps({'text': chunk, 'type': 'chunk'})}\n\n"
            
            # Store response in our history tracking
            _sessions[session_id]["messages"].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            elapsed = time.time() - start_time
            
            # Send completion (use display session_id)
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'chunks': chunk_count, 'time_seconds': round(elapsed, 2)})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# Session endpoints
@sessions_router.post("", response_model=SessionResponse)
async def create_session(request: SessionCreate) -> SessionResponse:
    """Create or get existing chat session for a candidate.
    
    If the candidate already has an active session, returns that session.
    Otherwise creates a new one.
    """
    # Verify candidate exists
    candidate_service = get_candidate_service()
    if not candidate_service.candidate_exists(request.candidate_id):
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {request.candidate_id} not found"
        )
    
    # Get or create session (reuses existing)
    session_id = get_or_create_session(request.candidate_id)
    
    return SessionResponse(
        session_id=session_id,
        candidate_id=request.candidate_id,
        created_at=_sessions[session_id]["created_at"],
        message_count=len(_sessions[session_id]["messages"])
    )


@sessions_router.get("/candidate/{candidate_id}", response_model=SessionResponse)
async def get_session_by_candidate(candidate_id: str) -> SessionResponse:
    """Get the active session for a candidate.
    
    Returns the existing session if one exists, or creates a new one.
    """
    candidate_service = get_candidate_service()
    if not candidate_service.candidate_exists(candidate_id):
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    
    session_id = get_or_create_session(candidate_id)
    session = _sessions[session_id]
    
    return SessionResponse(
        session_id=session_id,
        candidate_id=session["candidate_id"],
        created_at=session["created_at"],
        message_count=len(session["messages"])
    )


@sessions_router.delete("/candidate/{candidate_id}")
async def clear_candidate_session(candidate_id: str) -> dict:
    """Clear a candidate's session (for testing/reset).
    
    This removes the session and allows a fresh start.
    """
    if candidate_id in _candidate_sessions:
        session_id = _candidate_sessions[candidate_id]
        if session_id in _sessions:
            del _sessions[session_id]
        del _candidate_sessions[candidate_id]
        return {"status": "cleared", "candidate_id": candidate_id}
    
    return {"status": "no_session", "candidate_id": candidate_id}


@sessions_router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get session information by session ID."""
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


# Performance monitoring endpoints
perf_router = APIRouter(prefix="/perf", tags=["Performance"])


@perf_router.get("/stats")
async def get_performance_stats() -> dict:
    """Get performance and cache statistics."""
    cache = get_cache_service()
    job_service = get_job_service()
    candidate_service = get_candidate_service()
    async_embedding = get_async_embedding_service()
    
    return {
        "cache": cache.get_stats(),
        "embedding_queue": async_embedding.get_queue_stats(),
        "data": {
            "jobs_loaded": job_service.get_job_count(),
            "candidates_loaded": len(candidate_service.get_all_candidates()),
        },
        "sessions": {
            "active": len(_sessions),
            "total_messages": sum(len(s["messages"]) for s in _sessions.values())
        }
    }


@perf_router.post("/cache/clear")
async def clear_cache() -> dict:
    """Clear all cached data."""
    cache = get_cache_service()
    cleared = cache.clear()
    return {"cleared_entries": cleared, "status": "ok"}


@perf_router.post("/cache/cleanup")
async def cleanup_cache() -> dict:
    """Remove expired cache entries."""
    cache = get_cache_service()
    removed = cache.cleanup_expired()
    return {"removed_entries": removed, "status": "ok"}

