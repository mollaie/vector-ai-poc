#!/usr/bin/env python3
"""Create embeddings for jobs and upload to GCS."""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings
from src.services.data_generator import DataGenerator
from src.services.embeddings import EmbeddingService


def main():
    """Create embeddings for all jobs."""
    print("=" * 50)
    print("Vector AI PoC - Embedding Generation")
    print("=" * 50)
    
    settings = get_settings()
    
    # Check configuration
    if not settings.google_cloud_project:
        print("\nError: GOOGLE_CLOUD_PROJECT not set in .env file.")
        print("Please run: ./scripts/setup_gcp.sh <PROJECT_ID>")
        sys.exit(1)
    
    print(f"\nProject: {settings.google_cloud_project}")
    print(f"Region: {settings.google_cloud_region}")
    print(f"Embedding Model: {settings.embedding_model}")
    
    # Load jobs
    print("\nLoading jobs...")
    generator = DataGenerator()
    
    if not settings.jobs_file.exists():
        print("Error: Jobs file not found. Run generate_data.py first.")
        sys.exit(1)
    
    jobs = generator.load_jobs(settings.jobs_file)
    print(f"✓ Loaded {len(jobs)} jobs")
    
    # Initialize embedding service
    print("\nInitializing embedding service...")
    try:
        embedding_service = EmbeddingService()
        print("✓ Embedding service initialized")
    except Exception as e:
        print(f"Error initializing embedding service: {e}")
        print("\nMake sure you have:")
        print("  1. Authenticated with: gcloud auth application-default login")
        print("  2. Set the correct project in .env")
        sys.exit(1)
    
    # Generate embeddings
    print("\nGenerating embeddings for jobs...")
    embeddings_data = []
    
    # Process in batches
    batch_size = 5
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        texts = [job.to_embedding_text() for job in batch]
        
        try:
            embeddings = embedding_service.get_embeddings_batch(texts)
            
            for job, embedding in zip(batch, embeddings):
                embeddings_data.append({
                    "id": job.id,
                    "embedding": embedding
                })
            
            print(f"  Processed {min(i + batch_size, len(jobs))}/{len(jobs)} jobs...")
            
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            sys.exit(1)
    
    print(f"✓ Generated {len(embeddings_data)} embeddings")
    
    # Save embeddings locally
    embeddings_file = settings.data_dir / "job_embeddings.json"
    with open(embeddings_file, "w") as f:
        json.dump(embeddings_data, f)
    print(f"✓ Saved embeddings locally to {embeddings_file}")
    
    # Upload to GCS
    if settings.gcs_bucket:
        print(f"\nUploading embeddings to GCS bucket: {settings.gcs_bucket}...")
        try:
            from src.services.vector_search import VectorSearchService
            
            vector_service = VectorSearchService()
            gcs_uri = vector_service.upload_embeddings_to_gcs(
                embeddings_data,
                filename="job_embeddings.jsonl"
            )
            print(f"✓ Uploaded to {gcs_uri}")
            
        except Exception as e:
            print(f"Warning: Could not upload to GCS: {e}")
            print("You may need to upload manually or ensure bucket permissions are correct.")
    else:
        print("\nWarning: GCS_BUCKET not configured. Embeddings not uploaded to cloud.")
    
    print("\n" + "=" * 50)
    print("Embedding generation complete!")
    print("=" * 50)
    print("\nNext step: python scripts/deploy_index.py")


if __name__ == "__main__":
    main()

