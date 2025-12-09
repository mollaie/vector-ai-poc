"""Vertex AI Text Embedding Service."""

import asyncio
from typing import Optional

import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

from config.settings import get_settings


class EmbeddingService:
    """Service for generating text embeddings using Vertex AI."""
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """Initialize the embedding service.
        
        Args:
            project_id: Google Cloud project ID
            region: Google Cloud region
            model_name: Embedding model name (e.g., text-embedding-005)
        """
        settings = get_settings()
        self.project_id = project_id or settings.google_cloud_project
        self.region = region or settings.google_cloud_region
        self.model_name = model_name or settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.region)
        
        # Load the embedding model
        self._model: Optional[TextEmbeddingModel] = None
    
    @property
    def model(self) -> TextEmbeddingModel:
        """Lazy load the embedding model."""
        if self._model is None:
            self._model = TextEmbeddingModel.from_pretrained(self.model_name)
        return self._model
    
    def get_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            task_type: Type of embedding task. Options:
                - RETRIEVAL_DOCUMENT: For documents to be retrieved
                - RETRIEVAL_QUERY: For search queries
                - SEMANTIC_SIMILARITY: For comparing text similarity
                - CLASSIFICATION: For text classification
                - CLUSTERING: For text clustering
        
        Returns:
            List of embedding values
        """
        inputs = [TextEmbeddingInput(text=text, task_type=task_type)]
        embeddings = self.model.get_embeddings(inputs)
        return embeddings[0].values
    
    def get_embeddings_batch(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: int = 5
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            task_type: Type of embedding task
            batch_size: Number of texts per batch (max 5 for Vertex AI)
        
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            inputs = [TextEmbeddingInput(text=t, task_type=task_type) for t in batch_texts]
            embeddings = self.model.get_embeddings(inputs)
            all_embeddings.extend([e.values for e in embeddings])
        
        return all_embeddings
    
    def get_query_embedding(self, query: str) -> list[float]:
        """Generate embedding for a search query.
        
        Uses RETRIEVAL_QUERY task type optimized for search queries.
        
        Args:
            query: Search query text
        
        Returns:
            Query embedding vector
        """
        return self.get_embedding(query, task_type="RETRIEVAL_QUERY")
    
    def get_document_embedding(self, document: str) -> list[float]:
        """Generate embedding for a document.
        
        Uses RETRIEVAL_DOCUMENT task type optimized for documents.
        
        Args:
            document: Document text
        
        Returns:
            Document embedding vector
        """
        return self.get_embedding(document, task_type="RETRIEVAL_DOCUMENT")
    
    def generate_embedding(self, text: str) -> list[float]:
        """Alias for get_embedding (for compatibility).
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        return self.get_embedding(text)
    
    async def get_embedding_async(
        self,
        text: str,
        task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[float]:
        """Async wrapper for get_embedding.
        
        Args:
            text: Text to embed
            task_type: Type of embedding task
        
        Returns:
            Embedding vector
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.get_embedding(text, task_type)
        )
    
    async def get_embeddings_batch_async(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: int = 5
    ) -> list[list[float]]:
        """Async wrapper for get_embeddings_batch.
        
        Args:
            texts: List of texts to embed
            task_type: Type of embedding task
            batch_size: Number of texts per batch
        
        Returns:
            List of embedding vectors
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.get_embeddings_batch(texts, task_type, batch_size)
        )


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

