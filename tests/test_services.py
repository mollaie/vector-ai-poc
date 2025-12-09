"""Tests for service layer."""

import pytest
import json
from src.models.job import Job, ExperienceLevel, LocationType
from src.models.candidate import Candidate


class TestJobService:
    """Tests for JobService."""
    
    def test_get_job_exists(self, job_service):
        """Test getting an existing job."""
        job = job_service.get_job("job-test-001")
        
        assert job is not None
        assert job.id == "job-test-001"
        assert job.title == "Software Engineer"
    
    def test_get_job_not_exists(self, job_service):
        """Test getting a non-existent job."""
        job = job_service.get_job("non-existent-job")
        
        assert job is None
    
    def test_get_all_jobs(self, job_service):
        """Test getting all jobs."""
        jobs = job_service.get_all_jobs()
        
        assert len(jobs) == 4  # From fixtures
        assert all(isinstance(j, Job) for j in jobs)
    
    def test_get_jobs_paginated(self, job_service):
        """Test paginated job retrieval."""
        # Get first 2 jobs
        jobs = job_service.get_jobs_paginated(offset=0, limit=2)
        assert len(jobs) == 2
        
        # Get next 2 jobs
        jobs = job_service.get_jobs_paginated(offset=2, limit=2)
        assert len(jobs) == 2
        
        # Get with offset beyond data
        jobs = job_service.get_jobs_paginated(offset=10, limit=2)
        assert len(jobs) == 0
    
    def test_job_exists(self, job_service):
        """Test checking job existence."""
        assert job_service.job_exists("job-test-001") is True
        assert job_service.job_exists("non-existent") is False
    
    def test_get_job_count(self, job_service):
        """Test job count."""
        count = job_service.get_job_count()
        assert count == 4
    
    def test_search_jobs_by_ids(self, job_service):
        """Test searching jobs by IDs."""
        jobs = job_service.search_jobs_by_ids(["job-test-001", "job-test-002"])
        
        assert len(jobs) == 2
        assert jobs[0].id == "job-test-001"
        assert jobs[1].id == "job-test-002"
    
    def test_search_jobs_by_ids_partial(self, job_service):
        """Test searching with some invalid IDs."""
        jobs = job_service.search_jobs_by_ids(["job-test-001", "invalid-id"])
        
        assert len(jobs) == 1
        assert jobs[0].id == "job-test-001"
    
    def test_format_job_for_display(self, job_service, sample_job):
        """Test formatting job for display."""
        formatted = job_service.format_job_for_display(sample_job)
        
        assert formatted["id"] == "job-test-001"
        assert formatted["title"] == "Software Engineer"
        assert formatted["company"] == "TestCorp"
        assert "$150,000" in formatted["salary_range"]
    
    def test_format_job_with_match_score(self, job_service, sample_job):
        """Test formatting job with match score."""
        formatted = job_service.format_job_for_display(
            sample_job, 
            include_match_score=True, 
            match_score=0.85
        )
        
        assert formatted["match_score"] == 0.85
    
    def test_format_job_details(self, job_service, sample_job):
        """Test formatting full job details."""
        details = job_service.format_job_details(sample_job)
        
        assert details["id"] == "job-test-001"
        assert details["description"] == sample_job.description
        assert details["benefits"] == sample_job.benefits
        assert details["salary_min"] == 150000
        assert details["salary_max"] == 200000
    
    def test_reload_jobs(self, job_service, temp_jobs_file):
        """Test reloading jobs from file."""
        # Get initial count
        initial_count = job_service.get_job_count()
        
        # Add a new job to the file
        with open(temp_jobs_file) as f:
            jobs_data = json.load(f)
        
        jobs_data.append({
            "id": "job-new",
            "title": "New Job",
            "company": "NewCo",
            "description": "New job description",
            "required_skills": ["Skill1"],
            "preferred_skills": [],
            "experience_level": "junior",
            "min_years_experience": 0,
            "location_type": "remote",
            "location": None,
            "salary_min": 50000,
            "salary_max": 70000,
            "industry": "Tech",
            "department": "Engineering",
            "benefits": []
        })
        
        with open(temp_jobs_file, "w") as f:
            json.dump(jobs_data, f)
        
        # Reload and verify
        job_service.reload()
        assert job_service.get_job_count() == initial_count + 1


class TestCandidateService:
    """Tests for CandidateService."""
    
    def test_get_candidate_exists(self, candidate_service):
        """Test getting an existing candidate."""
        candidate = candidate_service.get_candidate("candidate-test-001")
        
        assert candidate is not None
        assert candidate.id == "candidate-test-001"
        assert candidate.name == "John Doe"
    
    def test_get_candidate_not_exists(self, candidate_service):
        """Test getting a non-existent candidate."""
        candidate = candidate_service.get_candidate("non-existent")
        
        assert candidate is None
    
    def test_get_all_candidates(self, candidate_service):
        """Test getting all candidates."""
        candidates = candidate_service.get_all_candidates()
        
        assert len(candidates) == 2  # From fixtures
        assert all(isinstance(c, Candidate) for c in candidates)
    
    def test_candidate_exists(self, candidate_service):
        """Test checking candidate existence."""
        assert candidate_service.candidate_exists("candidate-test-001") is True
        assert candidate_service.candidate_exists("non-existent") is False
    
    def test_update_preferences_salary(self, candidate_service):
        """Test updating salary preference."""
        success, fields = candidate_service.update_preferences(
            candidate_id="candidate-test-001",
            min_salary=200000
        )
        
        assert success is True
        assert len(fields) == 1
        assert "$200,000" in fields[0]
        
        # Verify change persisted
        candidate = candidate_service.get_candidate("candidate-test-001")
        assert candidate.min_salary == 200000
    
    def test_update_preferences_location(self, candidate_service):
        """Test updating location preference."""
        success, fields = candidate_service.update_preferences(
            candidate_id="candidate-test-001",
            preferred_location_types=["remote"]
        )
        
        assert success is True
        
        candidate = candidate_service.get_candidate("candidate-test-001")
        assert LocationType.REMOTE in candidate.preferred_location_types
    
    def test_update_preferences_industries(self, candidate_service):
        """Test updating industry preference."""
        success, fields = candidate_service.update_preferences(
            candidate_id="candidate-test-001",
            preferred_industries=["Healthcare", "Finance"]
        )
        
        assert success is True
        
        candidate = candidate_service.get_candidate("candidate-test-001")
        assert "Healthcare" in candidate.preferred_industries
        assert "Finance" in candidate.preferred_industries
    
    def test_update_preferences_not_found(self, candidate_service):
        """Test updating preferences for non-existent candidate."""
        success, fields = candidate_service.update_preferences(
            candidate_id="non-existent",
            min_salary=100000
        )
        
        assert success is False
        assert fields == []
    
    def test_accept_job(self, candidate_service):
        """Test accepting a job."""
        success = candidate_service.accept_job("candidate-test-001", "job-123")
        
        assert success is True
        
        candidate = candidate_service.get_candidate("candidate-test-001")
        assert candidate.accepted_job_id == "job-123"
    
    def test_accept_job_not_found(self, candidate_service):
        """Test accepting job for non-existent candidate."""
        success = candidate_service.accept_job("non-existent", "job-123")
        
        assert success is False
    
    def test_decline_jobs(self, candidate_service):
        """Test declining jobs."""
        success = candidate_service.decline_jobs(
            "candidate-test-001", 
            ["job-001", "job-002"]
        )
        
        assert success is True
        
        declined = candidate_service.get_declined_job_ids("candidate-test-001")
        assert "job-001" in declined
        assert "job-002" in declined
    
    def test_decline_jobs_no_duplicates(self, candidate_service):
        """Test that declining same job twice doesn't duplicate."""
        candidate_service.decline_jobs("candidate-test-001", ["job-001"])
        candidate_service.decline_jobs("candidate-test-001", ["job-001"])
        
        declined = candidate_service.get_declined_job_ids("candidate-test-001")
        assert declined.count("job-001") == 1
    
    def test_decline_jobs_not_found(self, candidate_service):
        """Test declining jobs for non-existent candidate."""
        success = candidate_service.decline_jobs("non-existent", ["job-001"])
        
        assert success is False
    
    def test_get_declined_job_ids(self, candidate_service):
        """Test getting declined job IDs."""
        candidate_service.decline_jobs("candidate-test-001", ["job-a", "job-b"])
        
        declined = candidate_service.get_declined_job_ids("candidate-test-001")
        
        assert len(declined) == 2
        assert "job-a" in declined
        assert "job-b" in declined
    
    def test_get_declined_job_ids_not_found(self, candidate_service):
        """Test getting declined jobs for non-existent candidate."""
        declined = candidate_service.get_declined_job_ids("non-existent")
        
        assert declined == []
    
    def test_format_candidate_profile(self, candidate_service, sample_candidate):
        """Test formatting candidate profile."""
        formatted = candidate_service.format_candidate_profile(sample_candidate)
        
        assert formatted["id"] == "candidate-test-001"
        assert formatted["name"] == "John Doe"
        assert formatted["years_experience"] == 8
        assert formatted["min_salary"] == 180000
        assert "remote" in formatted["preferred_location_types"]
    
    def test_format_candidate_summary(self, candidate_service, sample_candidate):
        """Test formatting candidate summary."""
        summary = candidate_service.format_candidate_summary(sample_candidate)
        
        assert summary["id"] == "candidate-test-001"
        assert summary["name"] == "John Doe"
        assert summary["current_title"] == "Senior Software Engineer"
        assert summary["years_experience"] == 8


class TestMatchingService:
    """Tests for MatchingService."""
    
    def test_search_jobs_for_candidate_vector(self, matching_service):
        """Test job search using vector search."""
        result = matching_service.search_jobs_for_candidate(
            candidate_id="candidate-test-001",
            num_results=3
        )
        
        assert "error" not in result
        assert "matches" in result
        assert result["search_type"] == "vector"
    
    def test_search_jobs_for_candidate_with_criteria(self, matching_service):
        """Test job search with additional criteria."""
        result = matching_service.search_jobs_for_candidate(
            candidate_id="candidate-test-001",
            additional_criteria="remote only, python",
            num_results=3
        )
        
        assert "error" not in result
        assert "matches" in result
    
    def test_search_jobs_candidate_not_found(self, matching_service):
        """Test job search for non-existent candidate."""
        result = matching_service.search_jobs_for_candidate(
            candidate_id="non-existent",
            num_results=3
        )
        
        assert "error" in result
    
    def test_search_jobs_fallback(self, job_service, candidate_service):
        """Test fallback search when vector service unavailable."""
        from unittest.mock import MagicMock
        from src.services.matching_service import MatchingService
        
        # Create a mock vector service without endpoint (simulates not configured)
        mock_no_endpoint = MagicMock()
        mock_no_endpoint.endpoint = None
        
        service = MatchingService(
            job_service=job_service,
            candidate_service=candidate_service,
            vector_service=mock_no_endpoint
        )
        
        result = service.search_jobs_for_candidate(
            candidate_id="candidate-test-001",
            num_results=3
        )
        
        assert "error" not in result
        assert result["search_type"] == "fallback"
        assert "note" in result
    
    def test_search_jobs_by_text(self, matching_service):
        """Test text-based job search."""
        result = matching_service.search_jobs_by_text(
            query="python developer",
            num_results=5
        )
        
        assert "results" in result
        assert result["query"] == "python developer"
    
    def test_search_jobs_by_text_no_vector(self, job_service, candidate_service):
        """Test text search without vector service endpoint."""
        from unittest.mock import MagicMock
        from src.services.matching_service import MatchingService
        
        # Create a mock vector service without endpoint
        mock_no_endpoint = MagicMock()
        mock_no_endpoint.endpoint = None
        
        service = MatchingService(
            job_service=job_service,
            candidate_service=candidate_service,
            vector_service=mock_no_endpoint
        )
        
        result = service.search_jobs_by_text(
            query="python developer",
            num_results=5
        )
        
        assert "error" in result
        assert "not available" in result["error"]

