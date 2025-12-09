"""Pytest configuration and shared fixtures."""

import json
import pytest
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.job import Job, ExperienceLevel, LocationType
from src.models.candidate import Candidate


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_job() -> Job:
    """Create a sample job for testing."""
    return Job(
        id="job-test-001",
        title="Software Engineer",
        company="TestCorp",
        description="Build great software with Python and AWS",
        required_skills=["Python", "AWS", "Docker"],
        preferred_skills=["Kubernetes", "Terraform"],
        experience_level=ExperienceLevel.SENIOR,
        min_years_experience=5,
        location_type=LocationType.REMOTE,
        location=None,
        salary_min=150000,
        salary_max=200000,
        industry="Technology",
        department="Engineering",
        benefits=["Health Insurance", "401k"]
    )


@pytest.fixture
def sample_bluecollar_job() -> Job:
    """Create a sample blue-collar job for testing."""
    return Job(
        id="job-bc-test-001",
        title="Delivery Driver",
        company="FastDelivery Inc",
        description="Deliver packages in the metro area. Pay: $18-22/hour.",
        required_skills=["Valid Driver's License", "Able to lift 25kg/55lbs"],
        preferred_skills=["Customer service skills"],
        experience_level=ExperienceLevel.JUNIOR,
        min_years_experience=0,
        location_type=LocationType.ONSITE,
        location="Chicago, IL",
        salary_min=37440,  # $18/hr * 2080
        salary_max=45760,  # $22/hr * 2080
        industry="Logistics",
        department="Delivery",
        benefits=["Weekly Pay", "Flexible Hours"]
    )


@pytest.fixture
def sample_candidate() -> Candidate:
    """Create a sample candidate for testing."""
    return Candidate(
        id="candidate-test-001",
        name="John Doe",
        email="john.doe@example.com",
        summary="Experienced software engineer with 8 years in backend development",
        skills=["Python", "AWS", "Docker", "PostgreSQL", "Redis"],
        years_experience=8,
        current_title="Senior Software Engineer",
        preferred_titles=["Staff Engineer", "Principal Engineer"],
        preferred_location_types=[LocationType.REMOTE, LocationType.HYBRID],
        preferred_locations=["San Francisco, CA", "New York, NY"],
        min_salary=180000,
        max_salary=250000,
        preferred_industries=["Technology", "Finance"],
        declined_job_ids=[],
        accepted_job_id=None
    )


@pytest.fixture
def sample_bluecollar_candidate() -> Candidate:
    """Create a sample blue-collar candidate for testing."""
    return Candidate(
        id="candidate-bc-test-001",
        name="Mike Johnson",
        email="mike.j@example.com",
        summary="Reliable driver with 5 years experience in delivery",
        skills=["Valid Driver's License", "Able to lift 50kg/110lbs", "Customer service skills"],
        years_experience=5,
        current_title="Delivery Driver",
        preferred_titles=["Route Driver", "Courier", "Van Driver"],
        preferred_location_types=[LocationType.ONSITE],
        preferred_locations=["Chicago, IL"],
        min_salary=41600,  # $20/hr
        max_salary=52000,  # $25/hr
        preferred_industries=["Logistics", "Retail"],
        declined_job_ids=[],
        accepted_job_id=None
    )


@pytest.fixture
def sample_jobs_list(sample_job, sample_bluecollar_job) -> list[Job]:
    """Create a list of sample jobs."""
    jobs = [sample_job, sample_bluecollar_job]
    
    # Add a few more jobs
    jobs.append(Job(
        id="job-test-002",
        title="Data Scientist",
        company="DataCorp",
        description="Analyze data and build ML models",
        required_skills=["Python", "SQL", "TensorFlow"],
        preferred_skills=["PyTorch"],
        experience_level=ExperienceLevel.MID,
        min_years_experience=3,
        location_type=LocationType.HYBRID,
        location="Boston, MA",
        salary_min=130000,
        salary_max=170000,
        industry="Technology",
        department="Data Science",
        benefits=["Health Insurance"]
    ))
    
    jobs.append(Job(
        id="job-bc-test-002",
        title="Warehouse Associate",
        company="BigWarehouse Co",
        description="Pick and pack orders in warehouse",
        required_skills=["Able to lift 25kg/55lbs", "Able to stand for 8+ hours"],
        preferred_skills=["Forklift Certification"],
        experience_level=ExperienceLevel.JUNIOR,
        min_years_experience=0,
        location_type=LocationType.ONSITE,
        location="Chicago, IL",
        salary_min=31200,  # $15/hr
        salary_max=39520,  # $19/hr
        industry="Warehousing",
        department="Operations",
        benefits=["Weekly Pay"]
    ))
    
    return jobs


@pytest.fixture
def sample_candidates_list(sample_candidate, sample_bluecollar_candidate) -> list[Candidate]:
    """Create a list of sample candidates."""
    return [sample_candidate, sample_bluecollar_candidate]


# ============================================================================
# Temporary File Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir(tmp_path) -> Path:
    """Create a temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_jobs_file(temp_data_dir, sample_jobs_list) -> Path:
    """Create a temporary jobs file with sample data."""
    jobs_file = temp_data_dir / "jobs.json"
    with open(jobs_file, "w") as f:
        json.dump([job.model_dump() for job in sample_jobs_list], f)
    return jobs_file


@pytest.fixture
def temp_candidates_file(temp_data_dir, sample_candidates_list) -> Path:
    """Create a temporary candidates file with sample data."""
    candidates_file = temp_data_dir / "candidates.json"
    with open(candidates_file, "w") as f:
        json.dump([c.model_dump() for c in sample_candidates_list], f)
    return candidates_file


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def job_service(temp_jobs_file):
    """Create a JobService with test data."""
    from src.services.job_service import JobService
    return JobService(jobs_file=temp_jobs_file)


@pytest.fixture
def candidate_service(temp_candidates_file):
    """Create a CandidateService with test data."""
    from src.services.candidate_service import CandidateService
    return CandidateService(candidates_file=temp_candidates_file)


@pytest.fixture
def mock_vector_service():
    """Create a mock VectorSearchService."""
    mock = MagicMock()
    mock.endpoint = MagicMock()
    mock.search_by_text.return_value = [
        {"id": "job-test-001", "distance": 0.2},
        {"id": "job-test-002", "distance": 0.3},
    ]
    return mock


@pytest.fixture
def matching_service(job_service, candidate_service, mock_vector_service):
    """Create a MatchingService with test dependencies."""
    from src.services.matching_service import MatchingService
    return MatchingService(
        job_service=job_service,
        candidate_service=candidate_service,
        vector_service=mock_vector_service
    )


# ============================================================================
# API Test Client Fixture
# ============================================================================

@pytest.fixture
def mock_candidate_service(temp_candidates_file):
    """Create and patch a CandidateService for API route tests."""
    from src.services.candidate_service import CandidateService
    import src.services.candidate_service as candidate_service_module
    
    test_service = CandidateService(candidates_file=temp_candidates_file)
    
    with patch.object(candidate_service_module, '_candidate_service', test_service):
        with patch.object(candidate_service_module, 'get_candidate_service', return_value=test_service):
            yield test_service


@pytest.fixture
def test_client(temp_jobs_file, temp_candidates_file):
    """Create a FastAPI test client with mocked services."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.services.job_service import JobService
    from src.services.candidate_service import CandidateService
    import src.services.job_service as job_service_module
    import src.services.candidate_service as candidate_service_module
    
    # Create services with test data
    test_job_service = JobService(jobs_file=temp_jobs_file)
    test_candidate_service = CandidateService(candidates_file=temp_candidates_file)
    
    # Patch the singleton getters
    with patch.object(job_service_module, '_job_service', test_job_service):
        with patch.object(candidate_service_module, '_candidate_service', test_candidate_service):
            with patch.object(job_service_module, 'get_job_service', return_value=test_job_service):
                with patch.object(candidate_service_module, 'get_candidate_service', return_value=test_candidate_service):
                    yield TestClient(app)

