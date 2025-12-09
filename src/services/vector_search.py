"""Vertex AI Vector Search Service."""

import json
import time
from typing import Optional
from pathlib import Path

from google.cloud import aiplatform
from google.cloud import storage

from config.settings import get_settings
from src.services.embeddings import EmbeddingService


class VectorSearchService:
    """Service for managing Vertex AI Vector Search operations."""
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        gcs_bucket: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """Initialize the Vector Search service.
        
        Args:
            project_id: Google Cloud project ID
            region: Google Cloud region
            gcs_bucket: GCS bucket for storing embeddings
            embedding_service: Service for generating embeddings
        """
        settings = get_settings()
        self.project_id = project_id or settings.google_cloud_project
        self.region = region or settings.google_cloud_region
        self.gcs_bucket = gcs_bucket or settings.gcs_bucket
        self.dimensions = settings.embedding_dimensions
        
        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.region)
        
        # Embedding service
        self._embedding_service = embedding_service
        
        # Index and endpoint references
        self._index: Optional[aiplatform.MatchingEngineIndex] = None
        self._endpoint: Optional[aiplatform.MatchingEngineIndexEndpoint] = None
        
        # Settings for index IDs
        self._index_id = settings.vector_search_index_id
        self._endpoint_id = settings.vector_search_endpoint_id
        self._deployed_index_id = settings.deployed_index_id
    
    @property
    def embedding_service(self) -> EmbeddingService:
        """Get or create the embedding service."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service
    
    @property
    def index(self) -> Optional[aiplatform.MatchingEngineIndex]:
        """Get the Vector Search index."""
        if self._index is None and self._index_id:
            try:
                self._index = aiplatform.MatchingEngineIndex(
                    index_name=self._index_id
                )
            except Exception:
                pass
        return self._index
    
    @property
    def endpoint(self) -> Optional[aiplatform.MatchingEngineIndexEndpoint]:
        """Get the Vector Search endpoint."""
        if self._endpoint is None and self._endpoint_id:
            try:
                self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
                    index_endpoint_name=self._endpoint_id
                )
            except Exception:
                pass
        return self._endpoint
    
    def upload_embeddings_to_gcs(
        self,
        embeddings_data: list[dict],
        filename: str = "embeddings.json"
    ) -> str:
        """Upload embeddings to GCS in JSONL format.
        
        Args:
            embeddings_data: List of dicts with 'id' and 'embedding' keys
            filename: Name of the file in GCS
        
        Returns:
            GCS URI of the uploaded file
        """
        storage_client = storage.Client(project=self.project_id)
        bucket = storage_client.bucket(self.gcs_bucket)
        blob = bucket.blob(f"embeddings/{filename}")
        
        # Convert to JSONL format required by Vector Search
        jsonl_content = "\n".join(
            json.dumps({"id": item["id"], "embedding": item["embedding"]})
            for item in embeddings_data
        )
        
        blob.upload_from_string(jsonl_content)
        
        return f"gs://{self.gcs_bucket}/embeddings/{filename}"
    
    def create_index(
        self,
        display_name: str = "job-vacancies-index",
        embeddings_gcs_uri: Optional[str] = None,
        description: str = "Vector search index for job vacancies"
    ) -> aiplatform.MatchingEngineIndex:
        """Create a new Vector Search index.
        
        Note: Index creation takes ~30-60 minutes.
        
        Args:
            display_name: Display name for the index
            embeddings_gcs_uri: GCS URI containing initial embeddings
            description: Description of the index
        
        Returns:
            Created MatchingEngineIndex
        """
        # Create the index with Tree-AH algorithm
        self._index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
            display_name=display_name,
            description=description,
            dimensions=self.dimensions,
            approximate_neighbors_count=10,
            distance_measure_type="COSINE_DISTANCE",
            leaf_node_embedding_count=500,
            leaf_nodes_to_search_percent=7,
            index_update_method="STREAM_UPDATE",
            contents_delta_uri=embeddings_gcs_uri,
        )
        
        self._index_id = self._index.resource_name
        print(f"Index created: {self._index_id}")
        print("Note: Index creation takes ~30-60 minutes to complete.")
        
        return self._index
    
    def create_endpoint(
        self,
        display_name: str = "job-vacancies-endpoint",
        description: str = "Endpoint for job vacancy vector search"
    ) -> aiplatform.MatchingEngineIndexEndpoint:
        """Create a Vector Search index endpoint.
        
        Args:
            display_name: Display name for the endpoint
            description: Description of the endpoint
        
        Returns:
            Created MatchingEngineIndexEndpoint
        """
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
            display_name=display_name,
            description=description,
            public_endpoint_enabled=True,
        )
        
        self._endpoint_id = self._endpoint.resource_name
        print(f"Endpoint created: {self._endpoint_id}")
        
        return self._endpoint
    
    def deploy_index(
        self,
        deployed_index_id: Optional[str] = None,
        machine_type: str = "e2-standard-16",
        min_replica_count: int = 1,
        max_replica_count: int = 1
    ) -> None:
        """Deploy the index to the endpoint.
        
        Note: Deployment takes ~20-30 minutes.
        
        Args:
            deployed_index_id: ID for the deployed index
            machine_type: Machine type for serving
            min_replica_count: Minimum number of replicas
            max_replica_count: Maximum number of replicas
        """
        if not self.index:
            raise ValueError("No index available. Create or load an index first.")
        if not self.endpoint:
            raise ValueError("No endpoint available. Create or load an endpoint first.")
        
        deployed_id = deployed_index_id or self._deployed_index_id
        
        self.endpoint.deploy_index(
            index=self.index,
            deployed_index_id=deployed_id,
            machine_type=machine_type,
            min_replica_count=min_replica_count,
            max_replica_count=max_replica_count,
        )
        
        print(f"Index deployed with ID: {deployed_id}")
        print("Note: Deployment takes ~20-30 minutes to complete.")
    
    def upsert_datapoints(
        self,
        datapoints: list[dict]
    ) -> None:
        """Upsert datapoints to the index using streaming update.
        
        Args:
            datapoints: List of dicts with 'id' and 'embedding' keys
        """
        if not self.index:
            raise ValueError("No index available. Create or load an index first.")
        
        # Convert to format expected by upsert
        index_datapoints = [
            aiplatform.MatchingEngineIndex.MatchingEngineIndexDataPoint(
                datapoint_id=dp["id"],
                feature_vector=dp["embedding"],
            )
            for dp in datapoints
        ]
        
        self.index.upsert_datapoints(datapoints=index_datapoints)
        print(f"Upserted {len(datapoints)} datapoints.")
    
    def remove_datapoints(self, datapoint_ids: list[str]) -> None:
        """Remove datapoints from the index.
        
        Args:
            datapoint_ids: List of datapoint IDs to remove
        """
        if not self.index:
            raise ValueError("No index available.")
        
        self.index.remove_datapoints(datapoint_ids=datapoint_ids)
        print(f"Removed {len(datapoint_ids)} datapoints.")
    
    def search(
        self,
        query_embedding: list[float],
        num_neighbors: int = 10,
        filter_ids: Optional[list[str]] = None
    ) -> list[dict]:
        """Search for nearest neighbors.
        
        Args:
            query_embedding: Query embedding vector
            num_neighbors: Number of neighbors to return
            filter_ids: Optional list of IDs to exclude from results
        
        Returns:
            List of dicts with 'id' and 'distance' keys
        """
        if not self.endpoint:
            raise ValueError("No endpoint available. Deploy the index first.")
        
        # Perform the search
        response = self.endpoint.find_neighbors(
            deployed_index_id=self._deployed_index_id,
            queries=[query_embedding],
            num_neighbors=num_neighbors,
        )
        
        # Parse results
        results = []
        if response and len(response) > 0:
            for neighbor in response[0]:
                result_id = neighbor.id
                # Skip filtered IDs
                if filter_ids and result_id in filter_ids:
                    continue
                results.append({
                    "id": result_id,
                    "distance": neighbor.distance,
                })
        
        return results[:num_neighbors]
    
    def search_by_text(
        self,
        query_text: str,
        num_neighbors: int = 10,
        filter_ids: Optional[list[str]] = None
    ) -> list[dict]:
        """Search using text query.
        
        Generates embedding from text and performs vector search.
        
        Args:
            query_text: Text query
            num_neighbors: Number of neighbors to return
            filter_ids: Optional list of IDs to exclude
        
        Returns:
            List of dicts with 'id' and 'distance' keys
        """
        # Generate query embedding
        query_embedding = self.embedding_service.get_query_embedding(query_text)
        
        return self.search(
            query_embedding=query_embedding,
            num_neighbors=num_neighbors,
            filter_ids=filter_ids
        )
    
    def load_index(self, index_id: str) -> aiplatform.MatchingEngineIndex:
        """Load an existing index by ID.
        
        Args:
            index_id: Full resource name of the index
        
        Returns:
            Loaded MatchingEngineIndex
        """
        self._index = aiplatform.MatchingEngineIndex(index_name=index_id)
        self._index_id = index_id
        return self._index
    
    def load_endpoint(self, endpoint_id: str) -> aiplatform.MatchingEngineIndexEndpoint:
        """Load an existing endpoint by ID.
        
        Args:
            endpoint_id: Full resource name of the endpoint
        
        Returns:
            Loaded MatchingEngineIndexEndpoint
        """
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=endpoint_id
        )
        self._endpoint_id = endpoint_id
        return self._endpoint
    
    def wait_for_index_creation(self, timeout_minutes: int = 90) -> bool:
        """Wait for index creation to complete.
        
        Args:
            timeout_minutes: Maximum time to wait
        
        Returns:
            True if index is ready, False if timeout
        """
        if not self._index:
            return False
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            try:
                self._index = aiplatform.MatchingEngineIndex(
                    index_name=self._index_id
                )
                # Check if index is in a ready state
                if self._index.gca_resource.metadata:
                    print("Index is ready!")
                    return True
            except Exception as e:
                print(f"Waiting for index... ({e})")
            
            time.sleep(60)  # Check every minute
        
        return False


# Singleton instance
_vector_search_service: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    """Get or create the vector search service singleton."""
    global _vector_search_service
    if _vector_search_service is None:
        _vector_search_service = VectorSearchService()
    return _vector_search_service

