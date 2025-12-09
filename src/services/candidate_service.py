"""Candidate Service - Handles all candidate-related operations.

This service follows the Single Responsibility Principle (SRP) by focusing
only on candidate-related business logic.
"""

import json
from typing import Optional
from pathlib import Path

from config.settings import get_settings
from src.models.job import LocationType
from src.models.candidate import Candidate


class CandidateService:
    """Service for managing candidate data and operations.
    
    Responsibilities:
    - Loading and caching candidate data
    - Saving candidate updates
    - Candidate profile management
    - Preference updates
    """
    
    def __init__(self, candidates_file: Optional[Path] = None):
        """Initialize the candidate service.
        
        Args:
            candidates_file: Path to candidates JSON file. Uses settings default if not provided.
        """
        settings = get_settings()
        self._candidates_file = candidates_file or settings.candidates_file
        self._candidates_cache: Optional[dict[str, Candidate]] = None
    
    @property
    def candidates(self) -> dict[str, Candidate]:
        """Lazy load and cache candidates from file."""
        if self._candidates_cache is None:
            self._load_candidates()
        return self._candidates_cache
    
    def _load_candidates(self) -> None:
        """Load candidates from JSON file into cache."""
        self._candidates_cache = {}
        if self._candidates_file.exists():
            with open(self._candidates_file) as f:
                data = json.load(f)
            self._candidates_cache = {c["id"]: Candidate(**c) for c in data}
    
    def _save_candidates(self) -> None:
        """Persist candidates to JSON file."""
        with open(self._candidates_file, "w") as f:
            json.dump(
                [c.model_dump() for c in self._candidates_cache.values()],
                f,
                indent=2
            )
    
    def reload(self) -> None:
        """Force reload candidates from file."""
        self._candidates_cache = None
        self._load_candidates()
    
    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """Get a candidate by ID.
        
        Args:
            candidate_id: The candidate identifier
            
        Returns:
            Candidate object if found, None otherwise
        """
        return self.candidates.get(candidate_id)
    
    def get_all_candidates(self) -> list[Candidate]:
        """Get all candidates.
        
        Returns:
            List of all Candidate objects
        """
        return list(self.candidates.values())
    
    def candidate_exists(self, candidate_id: str) -> bool:
        """Check if a candidate exists.
        
        Args:
            candidate_id: The candidate identifier
            
        Returns:
            True if candidate exists, False otherwise
        """
        return candidate_id in self.candidates
    
    def update_candidate(self, candidate: Candidate) -> None:
        """Update a candidate in the store.
        
        Args:
            candidate: The updated Candidate object
        """
        self._candidates_cache[candidate.id] = candidate
        self._save_candidates()
    
    def update_preferences(
        self,
        candidate_id: str,
        min_salary: Optional[int] = None,
        preferred_titles: Optional[list[str]] = None,
        preferred_location_types: Optional[list[str]] = None,
        preferred_industries: Optional[list[str]] = None,
        preferred_locations: Optional[list[str]] = None,
        skills: Optional[list[str]] = None
    ) -> tuple[bool, list[str]]:
        """Update a candidate's preferences.
        
        Args:
            candidate_id: The candidate identifier
            min_salary: New minimum salary requirement
            preferred_titles: New list of preferred job titles
            preferred_location_types: New list of location types (remote/hybrid/onsite)
            preferred_industries: New list of preferred industries
            preferred_locations: New list of preferred locations
            skills: Updated skills list
            
        Returns:
            Tuple of (success, list of updated fields)
        """
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            return False, []
        
        updated_fields = []
        
        if min_salary is not None:
            candidate.min_salary = min_salary
            updated_fields.append(f"min_salary: ${min_salary:,}")
        
        if preferred_titles is not None:
            candidate.preferred_titles = preferred_titles
            updated_fields.append(f"preferred_titles: {preferred_titles}")
        
        if preferred_location_types is not None:
            candidate.preferred_location_types = [
                LocationType(lt) for lt in preferred_location_types
            ]
            updated_fields.append(f"preferred_location_types: {preferred_location_types}")
        
        if preferred_industries is not None:
            candidate.preferred_industries = preferred_industries
            updated_fields.append(f"preferred_industries: {preferred_industries}")
        
        if preferred_locations is not None:
            candidate.preferred_locations = preferred_locations
            updated_fields.append(f"preferred_locations: {preferred_locations}")
        
        if skills is not None:
            candidate.skills = skills
            updated_fields.append(f"skills: {skills}")
        
        self.update_candidate(candidate)
        return True, updated_fields
    
    def accept_job(self, candidate_id: str, job_id: str) -> bool:
        """Record that a candidate has accepted a job.
        
        Args:
            candidate_id: The candidate identifier
            job_id: The accepted job identifier
            
        Returns:
            True if successful, False if candidate not found
        """
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            return False
        
        candidate.accepted_job_id = job_id
        self.update_candidate(candidate)
        return True
    
    def decline_jobs(self, candidate_id: str, job_ids: list[str]) -> bool:
        """Record that a candidate has declined jobs.
        
        Args:
            candidate_id: The candidate identifier
            job_ids: List of declined job identifiers
            
        Returns:
            True if successful, False if candidate not found
        """
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            return False
        
        for job_id in job_ids:
            if job_id not in candidate.declined_job_ids:
                candidate.declined_job_ids.append(job_id)
        
        self.update_candidate(candidate)
        return True
    
    def get_declined_job_ids(self, candidate_id: str) -> list[str]:
        """Get list of declined job IDs for a candidate.
        
        Args:
            candidate_id: The candidate identifier
            
        Returns:
            List of declined job IDs, empty list if candidate not found
        """
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            return []
        return candidate.declined_job_ids
    
    def format_candidate_profile(self, candidate: Candidate) -> dict:
        """Format candidate profile for API response.
        
        Args:
            candidate: Candidate object to format
            
        Returns:
            Dictionary with formatted candidate data
        """
        return {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "summary": candidate.summary,
            "skills": candidate.skills,
            "years_experience": candidate.years_experience,
            "current_title": candidate.current_title,
            "preferred_titles": candidate.preferred_titles,
            "preferred_location_types": [lt.value for lt in candidate.preferred_location_types],
            "min_salary": candidate.min_salary,
            "preferred_industries": candidate.preferred_industries,
            "declined_jobs_count": len(candidate.declined_job_ids),
            "has_accepted_job": candidate.accepted_job_id is not None
        }
    
    def format_candidate_summary(self, candidate: Candidate) -> dict:
        """Format candidate summary for list views.
        
        Args:
            candidate: Candidate object to format
            
        Returns:
            Dictionary with candidate summary
        """
        return {
            "id": candidate.id,
            "name": candidate.name,
            "current_title": candidate.current_title,
            "years_experience": candidate.years_experience,
            "has_accepted_job": candidate.accepted_job_id is not None
        }


# Singleton instance
_candidate_service: Optional[CandidateService] = None


def get_candidate_service() -> CandidateService:
    """Get or create the candidate service singleton.
    
    Returns:
        CandidateService instance
    """
    global _candidate_service
    if _candidate_service is None:
        _candidate_service = CandidateService()
    return _candidate_service

