"""Job Service - Handles all job-related operations.

This service follows the Single Responsibility Principle (SRP) by focusing
only on job-related business logic.
"""

import json
from typing import Optional
from pathlib import Path

from config.settings import get_settings
from src.models.job import Job


class JobService:
    """Service for managing job data and operations.
    
    Responsibilities:
    - Loading and caching job data
    - Retrieving job details
    - Job data transformations
    """
    
    def __init__(self, jobs_file: Optional[Path] = None):
        """Initialize the job service.
        
        Args:
            jobs_file: Path to jobs JSON file. Uses settings default if not provided.
        """
        settings = get_settings()
        self._jobs_file = jobs_file or settings.jobs_file
        self._jobs_cache: Optional[dict[str, Job]] = None
    
    @property
    def jobs(self) -> dict[str, Job]:
        """Lazy load and cache jobs from file."""
        if self._jobs_cache is None:
            self._load_jobs()
        return self._jobs_cache
    
    def _load_jobs(self) -> None:
        """Load jobs from JSON file into cache."""
        self._jobs_cache = {}
        if self._jobs_file.exists():
            with open(self._jobs_file) as f:
                data = json.load(f)
            self._jobs_cache = {job["id"]: Job(**job) for job in data}
    
    def reload(self) -> None:
        """Force reload jobs from file."""
        self._jobs_cache = None
        self._load_jobs()
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID.
        
        Args:
            job_id: The job identifier
            
        Returns:
            Job object if found, None otherwise
        """
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> list[Job]:
        """Get all jobs.
        
        Returns:
            List of all Job objects
        """
        return list(self.jobs.values())
    
    def get_jobs_paginated(self, offset: int = 0, limit: int = 20) -> list[Job]:
        """Get jobs with pagination.
        
        Args:
            offset: Number of jobs to skip
            limit: Maximum number of jobs to return
            
        Returns:
            List of Job objects
        """
        all_jobs = list(self.jobs.values())
        return all_jobs[offset:offset + limit]
    
    def search_jobs_by_ids(self, job_ids: list[str]) -> list[Job]:
        """Get multiple jobs by their IDs.
        
        Args:
            job_ids: List of job identifiers
            
        Returns:
            List of found Job objects
        """
        return [self.jobs[jid] for jid in job_ids if jid in self.jobs]
    
    def job_exists(self, job_id: str) -> bool:
        """Check if a job exists.
        
        Args:
            job_id: The job identifier
            
        Returns:
            True if job exists, False otherwise
        """
        return job_id in self.jobs
    
    def get_job_count(self) -> int:
        """Get total number of jobs.
        
        Returns:
            Total job count
        """
        return len(self.jobs)
    
    def format_job_for_display(self, job: Job, include_match_score: bool = False, match_score: float = 0.0) -> dict:
        """Format a job for display/API response.
        
        Args:
            job: Job object to format
            include_match_score: Whether to include match score
            match_score: The match score value
            
        Returns:
            Dictionary with formatted job data
        """
        result = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "description": job.description[:200] + "..." if len(job.description) > 200 else job.description,
            "required_skills": job.required_skills,
            "experience_level": job.experience_level.value,
            "location_type": job.location_type.value,
            "location": job.location,
            "salary_range": f"${job.salary_min:,} - ${job.salary_max:,}",
            "industry": job.industry,
        }
        
        if include_match_score:
            result["match_score"] = match_score
            
        return result
    
    def format_job_details(self, job: Job) -> dict:
        """Format full job details for API response.
        
        Args:
            job: Job object to format
            
        Returns:
            Dictionary with complete job data
        """
        return {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "experience_level": job.experience_level.value,
            "min_years_experience": job.min_years_experience,
            "location_type": job.location_type.value,
            "location": job.location,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_range": f"${job.salary_min:,} - ${job.salary_max:,}",
            "industry": job.industry,
            "department": job.department,
            "benefits": job.benefits
        }


# Singleton instance
_job_service: Optional[JobService] = None


def get_job_service() -> JobService:
    """Get or create the job service singleton.
    
    Returns:
        JobService instance
    """
    global _job_service
    if _job_service is None:
        _job_service = JobService()
    return _job_service

