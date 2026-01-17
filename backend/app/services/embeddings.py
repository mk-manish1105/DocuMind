from sentence_transformers import SentenceTransformer
import numpy as np

"""
Embedding service responsible for converting text into vector representations.

This module:
- Loads a pretrained sentence embedding model
- Provides utilities for embedding documents and user queries
- Ensures embeddings are normalized and compatible with FAISS indexing
"""

class EmbeddingService:
    """
    Wrapper around a sentence-transformer model used for semantic embeddings.

    The model is loaded once at startup and reused across requests to avoid
    repeated initialization overhead.
    """

    def __init__(self):
        # Load pretrained embedding model
        self.model = SentenceTransformer("intfloat/e5-large-v2")

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for a list of text chunks (documents).

        - Normalizes embeddings to unit length for cosine similarity
        - Returns float32 arrays suitable for FAISS indexing
        """
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return embeddings.astype("float32")

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate an embedding for a single query string.

        - Output shape is (1, embedding_dim) to match FAISS search requirements
        - Normalized for cosine similarity comparison
        """
        emb = self.model.encode(
            query,
            normalize_embeddings=True
        )
        return emb.reshape(1, -1).astype("float32")


# Singleton embedding service instance reused across the application
embedding_service = EmbeddingService()
