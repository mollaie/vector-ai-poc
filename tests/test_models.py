"""Tests for data models."""

import pytest
from src.models.job import Job, ExperienceLevel, LocationType, JobResponse
from src.models.candidate import Candidate, CandidateResponse


class TestJobModel:
    """Tests for Job model."""
    
    def test_job_creation(self, sample_job):
        """Test creating a job with all fields."""
        assert sample_job.id == "job-test-001"
        assert sample_job.title == "Software Engineer"
        assert sample_job.company == "TestCorp"
        assert sample_job.salary_min == 150000
        assert sample_job.salary_max == 200000
        assert sample_job.experience_level == ExperienceLevel.SENIOR
        assert sample_job.location_type == LocationType.REMOTE
    
    def test_job_required_skills(self, sample_job):
        """Test job required skills."""
        assert "Python" in sample_job.required_skills
        assert "AWS" in sample_job.required_skills
        assert len(sample_job.required_skills) == 3
    
    def test_job_to_embedding_text(self, sample_job):
        """Test job embedding text generation."""
        text = sample_job.to_embedding_text()
        
        assert "Software Engineer" in text
        assert "TestCorp" in text
        assert "Python" in text
        assert "AWS" in text
        assert "150,000" in text
        assert "200,000" in text
        assert "Technology" in text
    
    def test_bluecollar_job_embedding_text(self, sample_bluecollar_job):
        """Test blue-collar job embedding text."""
        text = sample_bluecollar_job.to_embedding_text()
        
        assert "Delivery Driver" in text
        assert "FastDelivery" in text
        assert "Driver's License" in text
    
    def test_job_response_from_job(self, sample_job):
        """Test JobResponse creation from Job."""
        response = JobResponse.from_job(sample_job)
        
        assert response.id == sample_job.id
        assert response.title == sample_job.title
        assert response.company == sample_job.company
        assert "$150,000" in response.salary_range
    
    def test_experience_level_enum(self):
        """Test ExperienceLevel enum values."""
        assert ExperienceLevel.JUNIOR.value == "junior"
        assert ExperienceLevel.MID.value == "mid"
        assert ExperienceLevel.SENIOR.value == "senior"
        assert ExperienceLevel.LEAD.value == "lead"
        assert ExperienceLevel.PRINCIPAL.value == "principal"
    
    def test_location_type_enum(self):
        """Test LocationType enum values."""
        assert LocationType.REMOTE.value == "remote"
        assert LocationType.HYBRID.value == "hybrid"
        assert LocationType.ONSITE.value == "onsite"


class TestCandidateModel:
    """Tests for Candidate model."""
    
    def test_candidate_creation(self, sample_candidate):
        """Test creating a candidate with all fields."""
        assert sample_candidate.id == "candidate-test-001"
        assert sample_candidate.name == "John Doe"
        assert sample_candidate.email == "john.doe@example.com"
        assert sample_candidate.years_experience == 8
        assert sample_candidate.min_salary == 180000
    
    def test_candidate_skills(self, sample_candidate):
        """Test candidate skills."""
        assert "Python" in sample_candidate.skills
        assert "AWS" in sample_candidate.skills
        assert len(sample_candidate.skills) == 5
    
    def test_candidate_to_embedding_text(self, sample_candidate):
        """Test candidate embedding text generation."""
        text = sample_candidate.to_embedding_text()
        
        assert "software engineer" in text.lower()
        assert "Python" in text
        assert "180,000" in text
    
    def test_bluecollar_candidate_embedding_text(self, sample_bluecollar_candidate):
        """Test blue-collar candidate embedding text."""
        text = sample_bluecollar_candidate.to_embedding_text()
        
        assert "driver" in text.lower()
        assert "Driver's License" in text
    
    def test_candidate_experience_level_junior(self):
        """Test experience level calculation for junior."""
        candidate = Candidate(
            id="c1",
            name="Junior Dev",
            email="junior@test.com",
            summary="New developer",
            skills=["Python"],
            years_experience=1,
            current_title="Junior Developer",
            preferred_titles=[],
            preferred_location_types=[],
            preferred_locations=[],
            min_salary=60000,
            max_salary=80000,
            preferred_industries=[],
            declined_job_ids=[]
        )
        assert candidate.get_experience_level() == ExperienceLevel.JUNIOR
    
    def test_candidate_experience_level_mid(self):
        """Test experience level calculation for mid."""
        candidate = Candidate(
            id="c2",
            name="Mid Dev",
            email="mid@test.com",
            summary="Developer",
            skills=["Python"],
            years_experience=4,
            current_title="Software Developer",
            preferred_titles=[],
            preferred_location_types=[],
            preferred_locations=[],
            min_salary=100000,
            max_salary=130000,
            preferred_industries=[],
            declined_job_ids=[]
        )
        assert candidate.get_experience_level() == ExperienceLevel.MID
    
    def test_candidate_experience_level_senior(self):
        """Test experience level calculation for senior."""
        candidate = Candidate(
            id="c3",
            name="Senior Dev",
            email="senior@test.com",
            summary="Senior developer",
            skills=["Python"],
            years_experience=7,
            current_title="Senior Developer",
            preferred_titles=[],
            preferred_location_types=[],
            preferred_locations=[],
            min_salary=150000,
            max_salary=200000,
            preferred_industries=[],
            declined_job_ids=[]
        )
        assert candidate.get_experience_level() == ExperienceLevel.SENIOR
    
    def test_candidate_response_from_candidate(self, sample_candidate):
        """Test CandidateResponse creation from Candidate."""
        response = CandidateResponse.from_candidate(sample_candidate)
        
        assert response.id == sample_candidate.id
        assert response.name == sample_candidate.name
        assert response.email == sample_candidate.email
        assert response.years_experience == sample_candidate.years_experience
    
    def test_candidate_declined_jobs(self, sample_candidate):
        """Test candidate declined jobs tracking."""
        assert sample_candidate.declined_job_ids == []
        
        sample_candidate.declined_job_ids.append("job-001")
        sample_candidate.declined_job_ids.append("job-002")
        
        assert len(sample_candidate.declined_job_ids) == 2
        assert "job-001" in sample_candidate.declined_job_ids
    
    def test_candidate_accepted_job(self, sample_candidate):
        """Test candidate accepted job tracking."""
        assert sample_candidate.accepted_job_id is None
        
        sample_candidate.accepted_job_id = "job-003"
        
        assert sample_candidate.accepted_job_id == "job-003"

