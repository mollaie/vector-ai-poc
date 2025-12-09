"""Matching Service - Handles job matching and search operations.

This service follows the Single Responsibility Principle (SRP) by focusing
only on matching candidates with jobs using various strategies.

Performance Pattern: Eventual Consistency
- Immediate: Search uses existing embeddings + text augmentation
- Background: Embeddings updated asynchronously for future searches
"""

import json
import logging
from typing import Optional

from src.models.job import Job
from src.models.candidate import Candidate
from src.services.job_service import get_job_service, JobService
from src.services.candidate_service import get_candidate_service, CandidateService
from src.services.vector_search import get_vector_search_service, VectorSearchService
from src.services.async_embedding_service import get_async_embedding_service

logger = logging.getLogger(__name__)


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
        
        Always fetches fresh candidate data from service.
        Uses vector search if available, falls back to skill matching otherwise.
        
        Args:
            candidate_id: ID of the candidate
            additional_criteria: Optional additional search text
            num_results: Number of results to return
            
        Returns:
            Dictionary with matches and metadata
        """
        # Force fresh data fetch
        candidate = self.candidate_service.get_candidate(candidate_id)
        if not candidate:
            return {"error": f"Candidate {candidate_id} not found"}
        
        # Build consistent search criteria from current preferences
        # This ensures updates are always reflected
        preference_criteria = self._build_preference_criteria(candidate)
        
        # Combine with any additional criteria
        if additional_criteria:
            full_criteria = f"{preference_criteria} | {additional_criteria}"
        else:
            full_criteria = preference_criteria
        
        # Try vector search first
        try:
            if self.vector_service and self.vector_service.endpoint:
                return self._vector_search(candidate, full_criteria, num_results)
        except Exception:
            pass
        
        # Fallback to skill-based matching
        return self._fallback_search(candidate, num_results)
    
    def _build_preference_criteria(self, candidate: Candidate) -> str:
        """Build search criteria from candidate's current preferences.
        
        This ensures preference changes are always reflected in search.
        
        Args:
            candidate: The candidate
            
        Returns:
            Preference criteria string
        """
        criteria_parts = []
        
        if candidate.min_salary > 0:
            criteria_parts.append(f"Minimum salary: ${candidate.min_salary:,}")
        
        if candidate.preferred_location_types:
            locations = [lt.value for lt in candidate.preferred_location_types]
            criteria_parts.append(f"Work style: {', '.join(locations)}")
        
        if candidate.preferred_industries:
            criteria_parts.append(f"Industries: {', '.join(candidate.preferred_industries)}")
        
        if candidate.preferred_titles:
            criteria_parts.append(f"Roles: {', '.join(candidate.preferred_titles)}")
        
        return " | ".join(criteria_parts) if criteria_parts else ""
    
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
        Strictly filters by salary and location preferences.
        
        Args:
            candidate: The candidate to match
            num_results: Number of results to return
            
        Returns:
            Dictionary with matches
        """
        scored_jobs = []
        filtered_count = 0
        
        for job in self.job_service.get_all_jobs():
            # Skip declined jobs
            if job.id in candidate.declined_job_ids:
                continue
            
            # STRICT: Filter out jobs below salary requirement
            if candidate.min_salary > 0 and job.salary_max < candidate.min_salary:
                filtered_count += 1
                continue
            
            # STRICT: Filter by location type if specified
            if candidate.preferred_location_types:
                if job.location_type not in candidate.preferred_location_types:
                    filtered_count += 1
                    continue
            
            # Score based on skill overlap
            skill_overlap = len(set(candidate.skills) & set(job.required_skills))
            
            # Bonus for meeting/exceeding salary
            salary_bonus = 1.0 if job.salary_min >= candidate.min_salary else 0.5
            
            # Bonus for industry match
            industry_bonus = 1.0 if job.industry in candidate.preferred_industries else 0.0
            
            score = (skill_overlap * 2) + salary_bonus + industry_bonus
            scored_jobs.append((job, score))
        
        # Sort by score descending
        scored_jobs.sort(key=lambda x: x[1], reverse=True)
        
        # Format top results
        matched_jobs = []
        for job, score in scored_jobs[:num_results]:
            match_score = round(min(score / 10, 1.0), 2)
            formatted = self.job_service.format_job_for_display(
                job, include_match_score=True, match_score=match_score
            )
            matched_jobs.append(formatted)
        
        return {
            "candidate_id": candidate.id,
            "matches": matched_jobs,
            "total_found": len(matched_jobs),
            "filtered_out": filtered_count,
            "search_type": "fallback",
            "note": f"Filtered {filtered_count} jobs not meeting requirements"
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
    
    def search_with_updated_preferences(
        self,
        candidate_id: str,
        preference_changes: dict,
        additional_criteria: Optional[str] = None,
        num_results: int = 3
    ) -> dict:
        """Search for jobs immediately after preference update.
        
        Smart search that:
        1. First tries STRICT matching (all criteria must match)
        2. If no results, tries SOFT matching (partial criteria)
        3. Returns suggestions for criteria that could be relaxed
        
        Args:
            candidate_id: ID of the candidate
            preference_changes: Dictionary of changed preferences
            additional_criteria: Optional additional search text
            num_results: Number of results to return
            
        Returns:
            Dictionary with matches, alternatives, and suggestions
        """
        candidate = self.candidate_service.get_candidate(candidate_id)
        if not candidate:
            return {"error": f"Candidate {candidate_id} not found"}
        
        # Build augmented search text (includes new preferences)
        augmented_criteria = self._build_augmented_criteria(
            candidate, preference_changes, additional_criteria
        )
        
        # Queue embedding update in background (non-blocking)
        self._queue_embedding_update(candidate, preference_changes)
        
        # Try STRICT search first
        try:
            if self.vector_service and self.vector_service.endpoint:
                result = self._vector_search_augmented(
                    candidate, augmented_criteria, num_results, preference_changes
                )
            else:
                result = self._fallback_search_augmented(
                    candidate, preference_changes, num_results
                )
        except Exception as e:
            logger.warning(f"Vector search failed, using fallback: {e}")
            result = self._fallback_search_augmented(
                candidate, preference_changes, num_results
            )
        
        result["preference_update"] = {
            "changes": preference_changes,
        }
        
        # If no strict matches, find SOFT matches and suggestions
        if result.get("total_found", 0) == 0:
            soft_result = self._soft_match_search(
                candidate, preference_changes, num_results
            )
            result["alternatives"] = soft_result.get("alternatives", [])
            result["suggestions"] = soft_result.get("suggestions", [])
            result["relaxed_criteria"] = soft_result.get("relaxed_criteria", {})
        
        return result
    
    def _build_augmented_criteria(
        self,
        candidate: Candidate,
        preference_changes: dict,
        additional_criteria: Optional[str]
    ) -> str:
        """Build augmented search criteria from preference changes.
        
        Args:
            candidate: The candidate
            preference_changes: Changed preferences
            additional_criteria: Additional search text
            
        Returns:
            Augmented criteria string
        """
        criteria_parts = []
        
        if "min_salary" in preference_changes:
            criteria_parts.append(
                f"Minimum salary requirement: ${preference_changes['min_salary']:,}"
            )
        
        if "preferred_location_types" in preference_changes:
            locations = preference_changes["preferred_location_types"]
            criteria_parts.append(f"Location preference: {', '.join(locations)}")
        
        if "preferred_industries" in preference_changes:
            industries = preference_changes["preferred_industries"]
            criteria_parts.append(f"Industry preference: {', '.join(industries)}")
        
        if "preferred_titles" in preference_changes:
            titles = preference_changes["preferred_titles"]
            criteria_parts.append(f"Looking for roles like: {', '.join(titles)}")
        
        if "skills" in preference_changes:
            skills = preference_changes["skills"]
            criteria_parts.append(f"Key skills: {', '.join(skills)}")
        
        if additional_criteria:
            criteria_parts.append(additional_criteria)
        
        return " | ".join(criteria_parts) if criteria_parts else ""
    
    def _queue_embedding_update(
        self,
        candidate: Candidate,
        preference_changes: dict
    ) -> Optional[str]:
        """Queue an embedding update in the background.
        
        Note: Currently disabled to reduce noise in logs.
        The preference changes are applied via text augmentation instead,
        which provides immediate results without embedding regeneration.
        
        Args:
            candidate: The candidate
            preference_changes: Changed preferences
            
        Returns:
            Task ID or None if queueing skipped/failed
        """
        # Skip background embedding updates for now
        # Preference changes are handled via text augmentation in _vector_search_augmented
        logger.debug(f"Skipping background embedding update for {candidate.id} - using text augmentation")
        return None
    
    def _vector_search_augmented(
        self,
        candidate: Candidate,
        augmented_criteria: str,
        num_results: int,
        preference_changes: Optional[dict] = None
    ) -> dict:
        """Perform vector search with augmented criteria and post-filtering.
        
        Uses existing candidate embedding + augmented text for immediate results.
        Applies STRICT post-filters for location type and job titles.
        
        Args:
            candidate: The candidate
            augmented_criteria: Augmented search criteria
            num_results: Number of results
            preference_changes: Preference changes to apply as filters
            
        Returns:
            Search results dictionary
        """
        preference_changes = preference_changes or {}
        
        # Build search query with augmented criteria
        search_text = candidate.to_embedding_text()
        if augmented_criteria:
            search_text += f"\n{augmented_criteria}"
        
        filter_ids = candidate.declined_job_ids
        
        # Get more results to account for post-filtering
        fetch_count = (num_results + len(filter_ids)) * 5
        
        results = self.vector_service.search_by_text(
            query_text=search_text,
            num_neighbors=fetch_count,
            filter_ids=filter_ids
        )
        
        # Get filter criteria
        required_location_types = preference_changes.get(
            "preferred_location_types",
            [lt.value for lt in candidate.preferred_location_types] if candidate.preferred_location_types else []
        )
        required_titles = preference_changes.get("preferred_titles", candidate.preferred_titles or [])
        min_salary = preference_changes.get("min_salary", candidate.min_salary)
        
        matched_jobs = []
        filtered_count = 0
        
        for result in results:
            if len(matched_jobs) >= num_results:
                break
                
            job = self.job_service.get_job(result["id"])
            if not job:
                continue
            
            # STRICT: Filter by location type if specified
            if required_location_types:
                if job.location_type.value not in required_location_types:
                    filtered_count += 1
                    continue
            
            # STRICT: Filter by salary if specified
            if min_salary > 0 and job.salary_max < min_salary:
                filtered_count += 1
                continue
            
            # STRICT: Filter by job title keywords if specified
            if required_titles:
                title_match = any(
                    title_keyword.lower() in job.title.lower()
                    for title_keyword in required_titles
                )
                if not title_match:
                    filtered_count += 1
                    continue
            
            match_score = round(1 - result["distance"], 2)
            formatted = self.job_service.format_job_for_display(
                job, include_match_score=True, match_score=match_score
            )
            matched_jobs.append(formatted)
        
        return {
            "candidate_id": candidate.id,
            "matches": matched_jobs,
            "total_found": len(matched_jobs),
            "filtered_out": filtered_count,
            "search_type": "vector_augmented",
            "filters_applied": {
                "location_types": required_location_types,
                "job_titles": required_titles,
                "min_salary": min_salary
            }
        }
    
    def _fallback_search_augmented(
        self,
        candidate: Candidate,
        preference_changes: dict,
        num_results: int
    ) -> dict:
        """Fallback search with STRICT filtering based on preference changes.
        
        Args:
            candidate: The candidate
            preference_changes: Changed preferences
            num_results: Number of results
            
        Returns:
            Search results dictionary
        """
        # Apply preference changes for filtering
        min_salary = preference_changes.get("min_salary", candidate.min_salary)
        preferred_locations = preference_changes.get(
            "preferred_location_types", 
            [lt.value for lt in candidate.preferred_location_types] if candidate.preferred_location_types else []
        )
        preferred_industries = preference_changes.get(
            "preferred_industries",
            candidate.preferred_industries
        )
        preferred_titles = preference_changes.get(
            "preferred_titles",
            candidate.preferred_titles or []
        )
        
        scored_jobs = []
        filtered_count = 0
        
        for job in self.job_service.get_all_jobs():
            if job.id in candidate.declined_job_ids:
                continue
            
            # STRICT: Filter by location type if specified
            if preferred_locations:
                if job.location_type.value not in preferred_locations:
                    filtered_count += 1
                    continue
            
            # STRICT: Filter by salary
            if min_salary > 0 and job.salary_max < min_salary:
                filtered_count += 1
                continue
            
            # STRICT: Filter by job title keywords if specified
            if preferred_titles:
                title_match = any(
                    title_keyword.lower() in job.title.lower()
                    for title_keyword in preferred_titles
                )
                if not title_match:
                    filtered_count += 1
                    continue
            
            score = 0.0
            
            # Skill overlap
            skill_overlap = len(set(candidate.skills) & set(job.required_skills))
            score += skill_overlap * 2
            
            # Salary match bonus
            if job.salary_min >= min_salary:
                score += 3
            
            # Industry match
            if job.industry in preferred_industries:
                score += 2
            
            # Title match bonus (already filtered, so this is extra)
            if preferred_titles:
                score += 3  # Bonus for matching title
            
            scored_jobs.append((job, score))
        
        scored_jobs.sort(key=lambda x: x[1], reverse=True)
        
        matched_jobs = []
        for job, score in scored_jobs[:num_results]:
            match_score = round(min(score / 10, 1.0), 2)
            formatted = self.job_service.format_job_for_display(
                job, include_match_score=True, match_score=match_score
            )
            matched_jobs.append(formatted)
        
        return {
            "candidate_id": candidate.id,
            "matches": matched_jobs,
            "total_found": len(matched_jobs),
            "filtered_out": filtered_count,
            "search_type": "fallback_augmented",
            "filters_applied": {
                "location_types": preferred_locations,
                "job_titles": preferred_titles,
                "min_salary": min_salary
            },
            "note": f"Filtered {filtered_count} jobs not meeting requirements"
        }
    
    def _soft_match_search(
        self,
        candidate: Candidate,
        preference_changes: dict,
        num_results: int
    ) -> dict:
        """Find SOFT matches when strict criteria returns nothing.
        
        Relaxes criteria one at a time to find alternatives and
        provides suggestions for what the user could do.
        
        Args:
            candidate: The candidate
            preference_changes: Requested preferences
            num_results: Number of results
            
        Returns:
            Dictionary with alternatives and suggestions
        """
        min_salary = preference_changes.get("min_salary", candidate.min_salary)
        preferred_locations = preference_changes.get(
            "preferred_location_types",
            [lt.value for lt in candidate.preferred_location_types] if candidate.preferred_location_types else []
        )
        preferred_titles = preference_changes.get(
            "preferred_titles",
            candidate.preferred_titles or []
        )
        
        alternatives = []
        suggestions = []
        relaxed_criteria = {}
        
        all_jobs = self.job_service.get_all_jobs()
        
        # Strategy 1: Relax LOCATION - find jobs matching title + salary but different location
        if preferred_titles:
            location_relaxed_jobs = []
            for job in all_jobs:
                if job.id in candidate.declined_job_ids:
                    continue
                if job.salary_max < min_salary:
                    continue
                # Check title match
                title_match = any(
                    t.lower() in job.title.lower() for t in preferred_titles
                )
                if title_match:
                    location_relaxed_jobs.append(job)
            
            if location_relaxed_jobs:
                relaxed_criteria["location_relaxed"] = len(location_relaxed_jobs)
                for job in location_relaxed_jobs[:num_results]:
                    alternatives.append({
                        **self.job_service.format_job_for_display(job),
                        "relaxed": "location",
                        "note": f"This is {job.location_type.value}, not remote"
                    })
                if preferred_locations:
                    other_locations = set(j.location_type.value for j in location_relaxed_jobs)
                    suggestions.append(
                        f"Found {len(location_relaxed_jobs)} {'/'.join(preferred_titles)} jobs "
                        f"but they are {', '.join(other_locations)}. Would you consider non-remote work?"
                    )
        
        # Strategy 2: Relax TITLE - find remote jobs in salary range
        if not alternatives and preferred_locations:
            title_relaxed_jobs = []
            for job in all_jobs:
                if job.id in candidate.declined_job_ids:
                    continue
                if job.salary_max < min_salary:
                    continue
                if job.location_type.value in preferred_locations:
                    title_relaxed_jobs.append(job)
            
            if title_relaxed_jobs:
                relaxed_criteria["title_relaxed"] = len(title_relaxed_jobs)
                for job in title_relaxed_jobs[:num_results]:
                    alternatives.append({
                        **self.job_service.format_job_for_display(job),
                        "relaxed": "title",
                        "note": f"Different role but remote and meets salary"
                    })
                suggestions.append(
                    f"No {'/'.join(preferred_titles) if preferred_titles else 'matching'} jobs found remote, "
                    f"but found {len(title_relaxed_jobs)} other remote jobs. "
                    f"Would you consider other roles?"
                )
        
        # Strategy 3: Find jobs that require specific skills/licenses
        if preferred_titles:
            skill_based_jobs = []
            skill_suggestions = set()
            
            for job in all_jobs:
                if job.id in candidate.declined_job_ids:
                    continue
                    
                # Check if job has relevant required skills
                for skill in job.required_skills:
                    skill_lower = skill.lower()
                    if any(t.lower() in skill_lower or skill_lower in t.lower() for t in preferred_titles):
                        skill_based_jobs.append((job, skill))
                        skill_suggestions.add(skill)
                        break
            
            if skill_based_jobs and not alternatives:
                relaxed_criteria["skill_based"] = len(skill_based_jobs)
                for job, skill in skill_based_jobs[:num_results]:
                    alternatives.append({
                        **self.job_service.format_job_for_display(job),
                        "relaxed": "skill_based",
                        "required_skill": skill,
                        "note": f"Requires: {skill}"
                    })
                
                if skill_suggestions:
                    skills_list = ", ".join(list(skill_suggestions)[:3])
                    suggestions.append(
                        f"Found jobs that require: {skills_list}. "
                        f"Do you have any of these qualifications?"
                    )
        
        # Strategy 4: Find closest salary matches if salary is the issue
        if not alternatives:
            salary_jobs = []
            for job in all_jobs:
                if job.id in candidate.declined_job_ids:
                    continue
                # Check title if specified
                if preferred_titles:
                    title_match = any(t.lower() in job.title.lower() for t in preferred_titles)
                    if not title_match:
                        continue
                # Any salary
                salary_jobs.append(job)
            
            if salary_jobs:
                # Sort by salary descending
                salary_jobs.sort(key=lambda j: j.salary_max, reverse=True)
                relaxed_criteria["any_salary"] = len(salary_jobs)
                
                for job in salary_jobs[:num_results]:
                    alternatives.append({
                        **self.job_service.format_job_for_display(job),
                        "relaxed": "salary",
                        "note": f"Salary: {job.format_salary()}"
                    })
                
                top_salary = salary_jobs[0].salary_max if salary_jobs else 0
                suggestions.append(
                    f"The highest paying {'/'.join(preferred_titles) if preferred_titles else ''} job "
                    f"offers ${top_salary:,}. Would you consider a lower salary?"
                )
        
        return {
            "alternatives": alternatives,
            "suggestions": suggestions,
            "relaxed_criteria": relaxed_criteria
        }


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

