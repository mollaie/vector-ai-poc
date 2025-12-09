"""Services package - Business logic layer.

This package contains all runtime services that power the job matching system.
Services follow SOLID principles and are designed for dependency injection.

Services:
- JobService: Manages job data and operations
- CandidateService: Manages candidate data and preferences
- MatchingService: Handles job-candidate matching algorithms
- EmbeddingService: Generates text embeddings via Vertex AI
- VectorSearchService: Performs vector similarity search

Architecture:
- Services are singletons for efficiency
- Each service has a single responsibility
- Services depend on abstractions (other services) not implementations
"""

from src.services.job_service import JobService, get_job_service
from src.services.candidate_service import CandidateService, get_candidate_service
from src.services.matching_service import MatchingService, get_matching_service
from src.services.embeddings import EmbeddingService, get_embedding_service
from src.services.vector_search import VectorSearchService, get_vector_search_service

__all__ = [
    # Job Service
    "JobService",
    "get_job_service",
    # Candidate Service
    "CandidateService", 
    "get_candidate_service",
    # Matching Service
    "MatchingService",
    "get_matching_service",
    # Embedding Service
    "EmbeddingService",
    "get_embedding_service",
    # Vector Search Service
    "VectorSearchService",
    "get_vector_search_service",
]
