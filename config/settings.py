"""Application configuration settings."""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Cloud Configuration
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    google_cloud_region: str = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    # Google Cloud Storage
    gcs_bucket: str = os.getenv("GCS_BUCKET", "")
    
    # Model Configuration
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-005")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Embedding dimensions for text-embedding-005
    embedding_dimensions: int = 768
    
    # Vector Search Configuration
    vector_search_index_id: str = os.getenv("VECTOR_SEARCH_INDEX_ID", "")
    vector_search_endpoint_id: str = os.getenv("VECTOR_SEARCH_ENDPOINT_ID", "")
    deployed_index_id: str = os.getenv("DEPLOYED_INDEX_ID", "job_vacancies_deployed")
    
    # API Configuration
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    
    # Data paths
    data_dir: Path = PROJECT_ROOT / "data"
    jobs_file: Path = PROJECT_ROOT / "data" / "jobs.json"
    candidates_file: Path = PROJECT_ROOT / "data" / "candidates.json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

