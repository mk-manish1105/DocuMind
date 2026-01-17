import faiss
import pickle
import numpy as np
from pathlib import Path
from .embeddings import embedding_service

"""
Document retrieval utilities based on FAISS.

This module is responsible for:
- Persisting and loading text chunks extracted from documents
- Building a FAISS index for semantic similarity search
- Loading an existing FAISS index from disk

The index uses cosine similarity via normalized inner product.
"""

def load_chunks(path: Path):
    """
    Load previously saved document text chunks from disk.

    Returns an empty list if the chunk file does not exist.
    """
    if not path.exists():
        return []
    with path.open("rb") as f:
        return pickle.load(f)


def save_chunks(path: Path, chunks: list):
    """
    Persist text chunks to disk using pickle.

    These chunks are later embedded and indexed for retrieval.
    """
    with path.open("wb") as f:
        pickle.dump(chunks, f)


def build_faiss_index(chunks: list[str], index_path: Path):
    """
    Build and persist a FAISS index from a list of text chunks.

    Steps:
    1. Generate vector embeddings for all chunks
    2. Normalize embeddings for cosine similarity
    3. Build an inner-product FAISS index
    4. Persist the index to disk
    """

    if not chunks:
        return None

    # 1️Generate embeddings for document chunks
    embeddings = embedding_service.embed_texts(chunks)

    #  Normalize embeddings (CRITICAL for cosine similarity)
    # Using L2 normalization allows inner product to behave as cosine similarity
    faiss.normalize_L2(embeddings)

    # Dimensionality of embeddings
    dim = embeddings.shape[1]

    # Create FAISS index using inner product similarity
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Persist index to disk for reuse across requests
    faiss.write_index(index, str(index_path))
    return index


def load_faiss_index(index_path: Path):
    """
    Load a previously built FAISS index from disk.

    Returns None if the index file does not exist.
    """
    if not index_path.exists():
        return None
    return faiss.read_index(str(index_path))
