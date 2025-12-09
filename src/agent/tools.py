"""Agent tools for job matching operations.

This module provides the tool functions that the ADK agent uses to interact
with the job matching system. Each tool wraps a service method and returns
JSON-formatted strings for the agent to process.

Design Principles:
- Tools are thin wrappers around services (Single Responsibility)
- Services are injected for testability (Dependency Inversion)
- All responses are JSON-formatted for agent consumption
"""

import json
from typing import Optional

from src.services.job_service import get_job_service
from src.services.candidate_service import get_candidate_service
from src.services.matching_service import get_matching_service


def search_jobs(
    candidate_id: str,
    additional_criteria: Optional[str] = None,
    num_results: int = 3
) -> str:
    """Search for job vacancies matching a candidate's profile.
    
    Args:
        candidate_id: ID of the candidate to find jobs for
        additional_criteria: Optional additional search criteria from the conversation
        num_results: Number of job matches to return (default: 3)
    
    Returns:
        JSON string with matching job details
    """
    matching_service = get_matching_service()
    result = matching_service.search_jobs_for_candidate(
        candidate_id=candidate_id,
        additional_criteria=additional_criteria,
        num_results=num_results
    )
    return json.dumps(result, indent=2)


def get_job_details(job_id: str) -> str:
    """Get detailed information about a specific job.
    
    Args:
        job_id: ID of the job to retrieve
    
    Returns:
        JSON string with full job details
    """
    job_service = get_job_service()
    job = job_service.get_job(job_id)
    
    if not job:
        return json.dumps({"error": f"Job {job_id} not found"})
    
    return json.dumps(job_service.format_job_details(job), indent=2)


def update_candidate_preferences(
    candidate_id: str,
    min_salary: Optional[int] = None,
    preferred_titles: Optional[list[str]] = None,
    preferred_location_types: Optional[list[str]] = None,
    preferred_industries: Optional[list[str]] = None,
    skills: Optional[list[str]] = None
) -> str:
    """Update a candidate's job search preferences.
    
    Args:
        candidate_id: ID of the candidate to update
        min_salary: New minimum salary requirement
        preferred_titles: New list of preferred job titles
        preferred_location_types: New list of preferred location types (remote/hybrid/onsite)
        preferred_industries: New list of preferred industries
        skills: Updated skills list
    
    Returns:
        JSON string confirming the update
    """
    candidate_service = get_candidate_service()
    
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
    
    return json.dumps({
        "status": "success",
        "candidate_id": candidate_id,
        "updated_fields": updated_fields,
        "message": "Preferences updated successfully. Ready to search for new job matches."
    }, indent=2)


def accept_job(candidate_id: str, job_id: str) -> str:
    """Record that a candidate has accepted a job offer.
    
    Args:
        candidate_id: ID of the candidate
        job_id: ID of the accepted job
    
    Returns:
        JSON string confirming the acceptance
    """
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


def decline_jobs(candidate_id: str, job_ids: list[str]) -> str:
    """Record that a candidate has declined job offers.
    
    Args:
        candidate_id: ID of the candidate
        job_ids: List of job IDs being declined
    
    Returns:
        JSON string confirming the decline and prompting for new search
    """
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


def get_candidate_profile(candidate_id: str) -> str:
    """Get the current profile and preferences of a candidate.
    
    Args:
        candidate_id: ID of the candidate
    
    Returns:
        JSON string with candidate profile
    """
    candidate_service = get_candidate_service()
    candidate = candidate_service.get_candidate(candidate_id)
    
    if not candidate:
        return json.dumps({"error": f"Candidate {candidate_id} not found"})
    
    return json.dumps(candidate_service.format_candidate_profile(candidate), indent=2)


def list_available_candidates() -> str:
    """List all available candidates for testing.
    
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
