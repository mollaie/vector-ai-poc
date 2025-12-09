#!/usr/bin/env python3
"""Deploy Vertex AI Vector Search index."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings
from src.services.vector_search import VectorSearchService


def update_env_file(key: str, value: str):
    """Update a key in the .env file."""
    env_file = project_root / ".env"
    
    if not env_file.exists():
        return
    
    with open(env_file, "r") as f:
        lines = f.readlines()
    
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break
    
    if not updated:
        lines.append(f"{key}={value}\n")
    
    with open(env_file, "w") as f:
        f.writelines(lines)


def main():
    """Create and deploy Vector Search index."""
    print("=" * 50)
    print("Vector AI PoC - Index Deployment")
    print("=" * 50)
    
    settings = get_settings()
    
    # Check configuration
    if not settings.google_cloud_project:
        print("\nError: GOOGLE_CLOUD_PROJECT not set in .env file.")
        print("Please run: ./scripts/setup_gcp.sh <PROJECT_ID>")
        sys.exit(1)
    
    if not settings.gcs_bucket:
        print("\nError: GCS_BUCKET not set in .env file.")
        sys.exit(1)
    
    print(f"\nProject: {settings.google_cloud_project}")
    print(f"Region: {settings.google_cloud_region}")
    print(f"GCS Bucket: {settings.gcs_bucket}")
    
    # Initialize vector search service
    print("\nInitializing Vector Search service...")
    try:
        vector_service = VectorSearchService()
        print("✓ Vector Search service initialized")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Check for existing index
    if settings.vector_search_index_id:
        print(f"\nExisting index found: {settings.vector_search_index_id}")
        response = input("Use existing index? (y/n): ")
        if response.lower() == "y":
            vector_service.load_index(settings.vector_search_index_id)
        else:
            settings.vector_search_index_id = ""
    
    # Create index if needed
    if not settings.vector_search_index_id:
        print("\n" + "-" * 50)
        print("Creating Vector Search Index")
        print("-" * 50)
        print("\nNote: Index creation takes approximately 30-60 minutes.")
        print("The script will create the index and return immediately.")
        print("You can check the status in the Google Cloud Console.")
        
        response = input("\nProceed with index creation? (y/n): ")
        if response.lower() != "y":
            print("Index creation cancelled.")
            sys.exit(0)
        
        embeddings_uri = f"gs://{settings.gcs_bucket}/embeddings/job_embeddings.jsonl"
        print(f"\nUsing embeddings from: {embeddings_uri}")
        
        try:
            index = vector_service.create_index(
                display_name="job-vacancies-index",
                embeddings_gcs_uri=embeddings_uri,
                description="Vector search index for job matching PoC"
            )
            
            # Update .env file
            update_env_file("VECTOR_SEARCH_INDEX_ID", index.resource_name)
            print(f"\n✓ Index creation initiated: {index.resource_name}")
            print("✓ Updated .env with VECTOR_SEARCH_INDEX_ID")
            
        except Exception as e:
            print(f"Error creating index: {e}")
            sys.exit(1)
    
    # Check for existing endpoint
    if settings.vector_search_endpoint_id:
        print(f"\nExisting endpoint found: {settings.vector_search_endpoint_id}")
        response = input("Use existing endpoint? (y/n): ")
        if response.lower() == "y":
            vector_service.load_endpoint(settings.vector_search_endpoint_id)
        else:
            settings.vector_search_endpoint_id = ""
    
    # Create endpoint if needed
    if not settings.vector_search_endpoint_id:
        print("\n" + "-" * 50)
        print("Creating Index Endpoint")
        print("-" * 50)
        
        response = input("\nProceed with endpoint creation? (y/n): ")
        if response.lower() != "y":
            print("Endpoint creation cancelled.")
            sys.exit(0)
        
        try:
            endpoint = vector_service.create_endpoint(
                display_name="job-vacancies-endpoint",
                description="Endpoint for job matching PoC"
            )
            
            # Update .env file
            update_env_file("VECTOR_SEARCH_ENDPOINT_ID", endpoint.resource_name)
            print(f"\n✓ Endpoint created: {endpoint.resource_name}")
            print("✓ Updated .env with VECTOR_SEARCH_ENDPOINT_ID")
            
        except Exception as e:
            print(f"Error creating endpoint: {e}")
            sys.exit(1)
    
    # Deploy index to endpoint
    print("\n" + "-" * 50)
    print("Deploying Index to Endpoint")
    print("-" * 50)
    print("\nNote: Deployment takes approximately 20-30 minutes.")
    
    response = input("\nProceed with deployment? (y/n): ")
    if response.lower() != "y":
        print("Deployment cancelled.")
        print("\nYou can deploy later by running this script again.")
        sys.exit(0)
    
    try:
        vector_service.deploy_index(
            deployed_index_id=settings.deployed_index_id,
            machine_type="e2-standard-16",
            min_replica_count=1,
            max_replica_count=1
        )
        
        print("\n✓ Deployment initiated")
        
    except Exception as e:
        print(f"Error deploying index: {e}")
        print("\nThis might be because the index is still being created.")
        print("Wait for index creation to complete, then run this script again.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Index Deployment Initiated!")
    print("=" * 50)
    print("\nWait for deployment to complete (20-30 minutes), then:")
    print("  python -m src.api.main")
    print("\nYou can monitor progress in the Google Cloud Console:")
    print(f"  https://console.cloud.google.com/vertex-ai/matching-engine/indexes?project={settings.google_cloud_project}")


if __name__ == "__main__":
    main()

