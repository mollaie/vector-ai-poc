"""Matching Service - Handles job matching and search operations.

This service follows the Single Responsibility Principle (SRP) by focusing
only on matching candidates with jobs using various strategies.
"""

import json
from typing import Optional

from src.models.job import Job
from src.models.candidate import Candidate
from src.services.job_service import get_job_service, JobService
from src.services.candidate_service import get_candidate_service, CandidateService
from src.services.vector_search import get_vector_search_service, VectorSearchService


class MatchingService:
    """Service for matching candidates with jobs.
    
    Responsibilities:
    - Vector-based semantic job matching
    - Fallback skill-based matching
    - Search result formatting
    
    This service implements the Strategy Pattern, allowing different
    matching algorithms (vector search vs fallback).
    """
    
    def __init__(
        self,
        job_service: Optional[JobService] = None,
        candidate_service: Optional[CandidateService] = None,
        vector_service: Optional[VectorSearchService] = None
    ):
        """Initialize the matching service with dependencies.
        
        Args:
            job_service: Service for job operations
            candidate_service: Service for candidate operations
            vector_service: Service for vector search operations
            
        Note: Uses Dependency Injection for testability and flexibility.
        """
        self._job_service = job_service
        self._candidate_service = candidate_service
        self._vector_service = vector_service
    
    @property
    def job_service(self) -> JobService:
        """Lazy load job service."""
        if self._job_service is None:
            self._job_service = get_job_service()
        return self._job_service
    
    @property
    def candidate_service(self) -> CandidateService:
        """Lazy load candidate service."""
        if self._candidate_service is None:
            self._candidate_service = get_candidate_service()
        return self._candidate_service
    
    @property
    def vector_service(self) -> Optional[VectorSearchService]:
        """Lazy load vector search service."""
        if self._vector_service is None:
            try:
                self._vector_service = get_vector_search_service()
            except Exception:
                pass  # Vector search not available
        return self._vector_service
    
    def search_jobs_for_candidate(
        self,
        candidate_id: str,
        additional_criteria: Optional[str] = None,
        num_results: int = 3
    ) -> dict:
        """Search for jobs matching a candidate's profile.
        
        Uses vector search if available, falls back to skill matching otherwise.
        
        Args:
            candidate_id: ID of the candidate
            additional_criteria: Optional additional search text
            num_results: Number of results to return
            
        Returns:
            Dictionary with matches and metadata
        """
        candidate = self.candidate_service.get_candidate(candidate_id)
        if not candidate:
            return {"error": f"Candidate {candidate_id} not found"}
        
        # Try vector search first
        try:
            if self.vector_service and self.vector_service.endpoint:
                return self._vector_search(candidate, additional_criteria, num_results)
        except Exception:
            pass
        
        # Fallback to skill-based matching
        return self._fallback_search(candidate, num_results)
    
    def _vector_search(
        self,
        candidate: Candidate,
        additional_criteria: Optional[str],
        num_results: int
    ) -> dict:
        """Perform vector-based semantic search.
        
        Args:
            candidate: The candidate to match
            additional_criteria: Optional additional search criteria
            num_results: Number of results to return
            
        Returns:
            Dictionary with matches
        """
        # Build search query from candidate profile
        search_text = candidate.to_embedding_text()
        if additional_criteria:
            search_text += f"\nAdditional requirements: {additional_criteria}"
        
        # Get filter IDs (declined jobs)
        filter_ids = candidate.declined_job_ids
        
        # Perform vector search
        results = self.vector_service.search_by_text(
            query_text=search_text,
            num_neighbors=num_results + len(filter_ids),
            filter_ids=filter_ids
        )
        
        # Format results
        matched_jobs = []
        for result in results[:num_results]:
            job = self.job_service.get_job(result["id"])
            if job:
                match_score = round(1 - result["distance"], 2)
                formatted = self.job_service.format_job_for_display(
                    job, include_match_score=True, match_score=match_score
                )
                matched_jobs.append(formatted)
        
        return {
            "candidate_id": candidate.id,
            "matches": matched_jobs,
            "total_found": len(matched_jobs),
            "search_type": "vector"
        }
    
    def _fallback_search(self, candidate: Candidate, num_results: int) -> dict:
        """Perform fallback skill-based matching.
        
        Used when vector search is not available.
        
        Args:
            candidate: The candidate to match
            num_results: Number of results to return
            
        Returns:
            Dictionary with matches
        """
        scored_jobs = []
        
        for job in self.job_service.get_all_jobs():
            if job.id in candidate.declined_job_ids:
                continue
            
            # Score based on skill overlap and salary match
            skill_overlap = len(set(candidate.skills) & set(job.required_skills))
            salary_match = 1.0 if job.salary_min >= candidate.min_salary else 0.5
            
            score = skill_overlap * salary_match
            scored_jobs.append((job, score))
        
        # Sort by score descending
        scored_jobs.sort(key=lambda x: x[1], reverse=True)
        
        # Format top results
        matched_jobs = []
        for job, score in scored_jobs[:num_results]:
            match_score = round(score / 10, 2)
            formatted = self.job_service.format_job_for_display(
                job, include_match_score=True, match_score=match_score
            )
            matched_jobs.append(formatted)
        
        return {
            "candidate_id": candidate.id,
            "matches": matched_jobs,
            "total_found": len(matched_jobs),
            "search_type": "fallback",
            "note": "Using fallback matching (vector search not configured)"
        }
    
    def search_jobs_by_text(
        self,
        query: str,
        num_results: int = 10,
        filter_ids: Optional[list[str]] = None
    ) -> dict:
        """Search jobs by text query.
        
        Args:
            query: Search query text
            num_results: Number of results to return
            filter_ids: Optional job IDs to exclude
            
        Returns:
            Dictionary with matches
        """
        try:
            if not self.vector_service or not self.vector_service.endpoint:
                return {"error": "Vector search not available", "results": []}
            
            results = self.vector_service.search_by_text(
                query_text=query,
                num_neighbors=num_results,
                filter_ids=filter_ids or []
            )
            
            matched_jobs = []
            for result in results:
                job = self.job_service.get_job(result["id"])
                if job:
                    match_score = round(1 - result["distance"], 2)
                    formatted = self.job_service.format_job_for_display(
                        job, include_match_score=True, match_score=match_score
                    )
                    matched_jobs.append(formatted)
            
            return {
                "query": query,
                "results": matched_jobs,
                "total": len(matched_jobs)
            }
            
        except Exception as e:
            return {"error": str(e), "results": []}


# Singleton instance
_matching_service: Optional[MatchingService] = None


def get_matching_service() -> MatchingService:
    """Get or create the matching service singleton.
    
    Returns:
        MatchingService instance
    """
    global _matching_service
    if _matching_service is None:
        _matching_service = MatchingService()
    return _matching_service

