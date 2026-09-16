"""Embedding model boundary.

Isolated behind one function so the embedding provider can be swapped
later (e.g. for a hosted embeddings API) without touching the vector
store, retriever, or ingestion pipeline. Currently uses ChromaDB's
built-in default embedding function - a small ONNX MiniLM model that
runs locally via onnxruntime, downloaded once and cached. No API key,
no PyTorch dependency, no per-call cost.
"""

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


def get_embedding_function():
    """Return the embedding function used to embed both documents and queries.

    Using the same function for both is required - a query embedded with
    a different model than the documents would not be comparable in the
    same vector space.
    """
    return DefaultEmbeddingFunction()
