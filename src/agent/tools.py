"""Agent tools for job matching operations.

This module provides the tool functions that the ADK agent uses to interact
with the job matching system. Each tool wraps a service method and returns
JSON-formatted strings for the agent to process.

Design Principles:
- Tools use ADK's ToolContext for session state management
- State tracks: candidate_id, last_search_results, preferences_updated
- Services are injected for testability (Dependency Inversion)
- All responses are JSON-formatted for agent consumption

Reference: https://cloud.google.com/blog/topics/developers-practitioners/remember-this-agent-state-and-memory-with-adk
"""

import json
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from src.services.job_service import get_job_service
from src.services.candidate_service import get_candidate_service
from src.services.matching_service import get_matching_service


def search_jobs(
    tool_context: ToolContext,
    candidate_id: str,
    additional_criteria: Optional[str] = None,
    num_results: int = 3
) -> str:
    """Search for job vacancies matching a candidate's profile.
    
    Uses ADK session state to track search history.
    
    Args:
        tool_context: ADK tool context for state management
        candidate_id: ID of the candidate to find jobs for
        additional_criteria: Optional additional search criteria from the conversation
        num_results: Number of job matches to return (default: 3)
    
    Returns:
        JSON string with matching job details
    """
    # Track candidate in session state
    state = tool_context.state
    state["candidate_id"] = candidate_id
    state["search_count"] = state.get("search_count", 0) + 1
    
    matching_service = get_matching_service()
    result = matching_service.search_jobs_for_candidate(
        candidate_id=candidate_id,
        additional_criteria=additional_criteria,
        num_results=num_results
    )
    
    # Store last search results in state for reference
    if "matches" in result:
        state["last_job_ids"] = [m["id"] for m in result["matches"]]
    
    return json.dumps(result, indent=2)


def get_job_details(tool_context: ToolContext, job_id: str) -> str:
    """Get detailed information about a specific job.
    
    Args:
        tool_context: ADK tool context for state management
        job_id: ID of the job to retrieve
    
    Returns:
        JSON string with full job details
    """
    # Track viewed jobs in state
    state = tool_context.state
    viewed_jobs = state.get("viewed_job_ids", [])
    if job_id not in viewed_jobs:
        viewed_jobs.append(job_id)
    state["viewed_job_ids"] = viewed_jobs
    
    job_service = get_job_service()
    job = job_service.get_job(job_id)
    
    if not job:
        return json.dumps({"error": f"Job {job_id} not found"})
    
    return json.dumps(job_service.format_job_details(job), indent=2)


def update_candidate_preferences(
    tool_context: ToolContext,
    candidate_id: str,
    min_salary: Optional[int] = None,
    preferred_titles: Optional[list[str]] = None,
    preferred_location_types: Optional[list[str]] = None,
    preferred_industries: Optional[list[str]] = None,
    skills: Optional[list[str]] = None,
    search_immediately: bool = True,
    num_results: int = 3
) -> str:
    """Update preferences AND search for matching jobs in one call.
    
    This is optimized for speed:
    - Updates preferences in database immediately
    - Searches using new preferences + text augmentation (no embedding wait)
    - Queues embedding update in background for future searches
    - Tracks preference changes in ADK session state
    
    Args:
        tool_context: ADK tool context for state management
        candidate_id: ID of the candidate to update
        min_salary: New minimum salary requirement
        preferred_titles: New list of preferred job titles
        preferred_location_types: New list of preferred location types (remote/hybrid/onsite)
        preferred_industries: New list of preferred industries
        skills: Updated skills list
        search_immediately: If True, also returns matching jobs (default: True)
        num_results: Number of job results to return
    
    Returns:
        JSON with updated preferences AND matching jobs
    """
    # Track in session state
    state = tool_context.state
    state["candidate_id"] = candidate_id
    state["preferences_updated"] = True
    
    candidate_service = get_candidate_service()
    matching_service = get_matching_service()
    
    # Build preference changes dict
    preference_changes = {}
    if min_salary is not None:
        preference_changes["min_salary"] = min_salary
        state["current_min_salary"] = min_salary
    if preferred_titles is not None:
        preference_changes["preferred_titles"] = preferred_titles
    if preferred_location_types is not None:
        preference_changes["preferred_location_types"] = preferred_location_types
        state["current_location_types"] = preferred_location_types
    if preferred_industries is not None:
        preference_changes["preferred_industries"] = preferred_industries
    if skills is not None:
        preference_changes["skills"] = skills
    
    # Update preferences in database
    success, updated_fields = candidate_service.update_preferences(
        candidate_id=candidate_id,
        min_salary=min_salary,
        preferred_titles=preferred_titles,
        preferred_location_types=preferred_location_types,
        preferred_industries=preferred_industries,
        skills=skills
    )
    
    if not success:
        return json.dumps({"error": f"Candidate {candidate_id} not found"})
    
    result = {
        "status": "success",
        "candidate_id": candidate_id,
        "updated_fields": updated_fields,
    }
    
    # Search immediately with updated preferences (parallel pattern)
    if search_immediately and preference_changes:
        search_result = matching_service.search_with_updated_preferences(
            candidate_id=candidate_id,
            preference_changes=preference_changes,
            num_results=num_results
        )
        result["matches"] = search_result.get("matches", [])
        # Store in state
        if result["matches"]:
            state["last_job_ids"] = [m["id"] for m in result["matches"]]
        result["total_found"] = search_result.get("total_found", 0)
        result["search_type"] = search_result.get("search_type", "unknown")
        
        # IMPORTANT: Pass through close_alternatives for salary tolerance matching
        if "close_alternatives" in search_result:
            result["close_alternatives"] = search_result["close_alternatives"]
        
        # Pass through the smart note
        if "note" in search_result:
            result["note"] = search_result["note"]
        
        # Build appropriate message
        if result["total_found"] > 0:
            result["message"] = f"Updated preferences and found {result['total_found']} matching jobs."
        elif "close_alternatives" in result and len(result["close_alternatives"]) > 0:
            result["message"] = f"No exact matches at your criteria, but found {len(result['close_alternatives'])} close alternatives within 15% of your salary target."
        else:
            result["message"] = "Updated preferences but no matching jobs found. Consider adjusting your criteria."
    else:
        result["message"] = "Preferences updated successfully."
    
    return json.dumps(result, indent=2)


def accept_job(tool_context: ToolContext, candidate_id: str, job_id: str) -> str:
    """Record that a candidate has accepted a job offer.
    
    Args:
        tool_context: ADK tool context for state management
        candidate_id: ID of the candidate
        job_id: ID of the accepted job
    
    Returns:
        JSON string confirming the acceptance
    """
    # Track in state
    state = tool_context.state
    state["candidate_id"] = candidate_id
    state["accepted_job_id"] = job_id
    state["workflow_complete"] = True
    
    candidate_service = get_candidate_service()
    job_service = get_job_service()
    
    if not candidate_service.candidate_exists(candidate_id):
        return json.dumps({"error": f"Candidate {candidate_id} not found"})
    
    job = job_service.get_job(job_id)
    if not job:
        return json.dumps({"error": f"Job {job_id} not found"})
    
    candidate_service.accept_job(candidate_id, job_id)
    
    return json.dumps({
        "status": "success",
        "candidate_id": candidate_id,
        "accepted_job": {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "salary_range": f"${job.salary_min:,} - ${job.salary_max:,}"
        },
        "message": f"Congratulations! You have accepted the {job.title} position at {job.company}."
    }, indent=2)


def decline_jobs(tool_context: ToolContext, candidate_id: str, job_ids: list[str]) -> str:
    """Record that a candidate has declined job offers.
    
    Args:
        tool_context: ADK tool context for state management
        candidate_id: ID of the candidate
        job_ids: List of job IDs being declined
    
    Returns:
        JSON string confirming the decline and prompting for new search
    """
    # Track in state
    state = tool_context.state
    state["candidate_id"] = candidate_id
    declined_list = state.get("declined_job_ids", [])
    declined_list.extend(job_ids)
    state["declined_job_ids"] = declined_list
    
    candidate_service = get_candidate_service()
    
    if not candidate_service.candidate_exists(candidate_id):
        return json.dumps({"error": f"Candidate {candidate_id} not found"})
    
    candidate_service.decline_jobs(candidate_id, job_ids)
    declined_count = len(candidate_service.get_declined_job_ids(candidate_id))
    
    return json.dumps({
        "status": "success",
        "candidate_id": candidate_id,
        "declined_jobs_count": declined_count,
        "message": "Jobs declined. Would you like to update your preferences or search for new matches?"
    }, indent=2)


def get_candidate_profile(tool_context: ToolContext, candidate_id: str) -> str:
    """Get the current profile and preferences of a candidate.
    
    Args:
        tool_context: ADK tool context for state management
        candidate_id: ID of the candidate
    
    Returns:
        JSON string with candidate profile
    """
    # Track in state
    state = tool_context.state
    state["candidate_id"] = candidate_id
    
    candidate_service = get_candidate_service()
    candidate = candidate_service.get_candidate(candidate_id)
    
    if not candidate:
        return json.dumps({"error": f"Candidate {candidate_id} not found"})
    
    # Store current preferences in state for quick reference
    profile = candidate_service.format_candidate_profile(candidate)
    state["current_min_salary"] = profile.get("min_salary")
    state["current_location_types"] = profile.get("preferred_location_types")
    
    return json.dumps(profile, indent=2)


def list_available_candidates(tool_context: ToolContext) -> str:
    """List all available candidates for testing.
    
    Args:
        tool_context: ADK tool context for state management
    
    Returns:
        JSON string with list of candidate summaries
    """
    candidate_service = get_candidate_service()
    candidates = candidate_service.get_all_candidates()
    
    summaries = [
        candidate_service.format_candidate_summary(c)
        for c in candidates
    ]
    
    return json.dumps({
        "total_candidates": len(summaries),
        "candidates": summaries
    }, indent=2)


# Legacy exports for backwards compatibility with routes.py
def _load_jobs():
    """Legacy: Load jobs (use job_service instead)."""
    return {job.id: job for job in get_job_service().get_all_jobs()}


def _load_candidates():
    """Legacy: Load candidates (use candidate_service instead)."""
    return {c.id: c for c in get_candidate_service().get_all_candidates()}


def _candidates_store():
    """Legacy: Get candidates store (use candidate_service instead)."""
    return _load_candidates()


def _save_candidates():
    """Legacy: Save candidates (handled by candidate_service)."""
    pass  # Now handled internally by CandidateService
