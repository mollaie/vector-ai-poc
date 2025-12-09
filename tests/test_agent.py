"""Tests for the job matching agent."""

import json
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.job import Job, ExperienceLevel, LocationType
from src.models.candidate import Candidate
from src.services.data_generator import DataGenerator


class TestDataGenerator:
    """Tests for data generation."""
    
    def test_generate_single_job(self):
        """Test generating a single job."""
        generator = DataGenerator(seed=42)
        job = generator.generate_job()
        
        assert job.id is not None
        assert job.title is not None
        assert job.company is not None
        assert job.salary_min > 0
        assert job.salary_max > job.salary_min
        assert len(job.required_skills) > 0
    
    def test_generate_single_candidate(self):
        """Test generating a single candidate."""
        generator = DataGenerator(seed=42)
        candidate = generator.generate_candidate()
        
        assert candidate.id is not None
        assert candidate.name is not None
        assert candidate.email is not None
        assert len(candidate.skills) > 0
    
    def test_generate_multiple_jobs(self):
        """Test generating multiple jobs."""
        generator = DataGenerator(seed=42)
        jobs = generator.generate_jobs(count=10)
        
        assert len(jobs) == 10
        # Check all IDs are unique
        ids = [job.id for job in jobs]
        assert len(ids) == len(set(ids))
    
    def test_generate_multiple_candidates(self):
        """Test generating multiple candidates."""
        generator = DataGenerator(seed=42)
        candidates = generator.generate_candidates(count=5)
        
        assert len(candidates) == 5
        # Check all IDs are unique
        ids = [c.id for c in candidates]
        assert len(ids) == len(set(ids))
    
    def test_job_embedding_text(self):
        """Test job embedding text generation."""
        job = Job(
            id="test-job",
            title="Software Engineer",
            company="TechCorp",
            description="Build great software",
            required_skills=["Python", "AWS"],
            preferred_skills=["Docker"],
            experience_level=ExperienceLevel.SENIOR,
            min_years_experience=5,
            location_type=LocationType.REMOTE,
            location=None,
            salary_min=150000,
            salary_max=200000,
            industry="Technology",
            department="Engineering",
            benefits=["Health Insurance"]
        )
        
        text = job.to_embedding_text()
        
        assert "Software Engineer" in text
        assert "TechCorp" in text
        assert "Python" in text
        assert "150,000" in text
    
    def test_candidate_embedding_text(self):
        """Test candidate embedding text generation."""
        candidate = Candidate(
            id="test-candidate",
            name="John Doe",
            email="john@example.com",
            summary="Experienced developer",
            skills=["Python", "JavaScript"],
            years_experience=8,
            current_title="Senior Engineer",
            preferred_titles=["Staff Engineer"],
            preferred_location_types=[LocationType.REMOTE],
            preferred_locations=[],
            min_salary=180000,
            max_salary=250000,
            preferred_industries=["Technology"],
            declined_job_ids=[],
            accepted_job_id=None
        )
        
        text = candidate.to_embedding_text()
        
        assert "Experienced developer" in text
        assert "Python" in text
        assert "180,000" in text


class TestJobModel:
    """Tests for Job model."""
    
    def test_job_creation(self):
        """Test creating a job."""
        job = Job(
            id="job-001",
            title="Backend Developer",
            company="StartupX",
            description="Join our team",
            required_skills=["Python"],
            preferred_skills=[],
            experience_level=ExperienceLevel.MID,
            min_years_experience=3,
            location_type=LocationType.HYBRID,
            location="San Francisco",
            salary_min=120000,
            salary_max=160000,
            industry="Technology",
            department="Engineering",
            benefits=[]
        )
        
        assert job.id == "job-001"
        assert job.experience_level == ExperienceLevel.MID
        assert job.location_type == LocationType.HYBRID
    
    def test_experience_levels(self):
        """Test experience level enum values."""
        assert ExperienceLevel.JUNIOR.value == "junior"
        assert ExperienceLevel.SENIOR.value == "senior"
        assert ExperienceLevel.PRINCIPAL.value == "principal"


class TestCandidateModel:
    """Tests for Candidate model."""
    
    def test_candidate_creation(self):
        """Test creating a candidate."""
        candidate = Candidate(
            id="candidate-001",
            name="Jane Smith",
            email="jane@example.com",
            summary="Full-stack developer",
            skills=["React", "Node.js"],
            years_experience=5,
            current_title="Software Engineer",
            preferred_titles=["Senior Engineer"],
            preferred_location_types=[LocationType.REMOTE],
            preferred_locations=[],
            min_salary=150000,
            max_salary=None,
            preferred_industries=["Technology"],
            declined_job_ids=[],
            accepted_job_id=None
        )
        
        assert candidate.id == "candidate-001"
        assert candidate.years_experience == 5
    
    def test_experience_level_calculation(self):
        """Test automatic experience level calculation."""
        junior = Candidate(
            id="c1", name="A", email="a@b.com", summary="", skills=[],
            years_experience=1, preferred_location_types=[], preferred_locations=[],
            min_salary=0, preferred_industries=[], declined_job_ids=[]
        )
        assert junior.get_experience_level() == ExperienceLevel.JUNIOR
        
        senior = Candidate(
            id="c2", name="B", email="b@b.com", summary="", skills=[],
            years_experience=6, preferred_location_types=[], preferred_locations=[],
            min_salary=0, preferred_industries=[], declined_job_ids=[]
        )
        assert senior.get_experience_level() == ExperienceLevel.SENIOR


class TestAgentTools:
    """Tests for agent tools."""
    
    @pytest.fixture
    def setup_test_data(self, tmp_path):
        """Set up test data files."""
        # This would set up test data for tool testing
        pass
    
    def test_tools_exist(self):
        """Test that all required tools are defined."""
        from src.agent.tools import (
            search_jobs,
            get_job_details,
            update_candidate_preferences,
            accept_job,
            decline_jobs,
            get_candidate_profile,
            list_available_candidates,
        )
        
        # All tools should be callable
        assert callable(search_jobs)
        assert callable(get_job_details)
        assert callable(update_candidate_preferences)
        assert callable(accept_job)
        assert callable(decline_jobs)
        assert callable(get_candidate_profile)
        assert callable(list_available_candidates)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

