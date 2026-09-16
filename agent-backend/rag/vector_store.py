"""Persistent ChromaDB wrapper: ingest chunks, query for nearest chunks.

The collection is configured to use cosine distance so that similarity
scores are intuitive (1.0 = identical, 0.0 = unrelated) and thresholding
in `retriever.py` is easy to reason about.
"""

from dataclasses import asdict
from functools import lru_cache

import chromadb

from rag.chunker import Chunk
from rag.embeddings import get_embedding_function


class VectorStore:
    def __init__(self, persist_directory: str, collection_name: str):
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=get_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )

    def ingest(self, chunks: list[Chunk]) -> int:
        """Upsert chunks into the collection. Returns the number ingested."""
        if not chunks:
            return 0

        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {k: v for k, v in asdict(chunk).items() if k not in ("chunk_id", "text")}
                for chunk in chunks
            ],
        )
        return len(chunks)

    def count(self) -> int:
        return self._collection.count()

    def query(self, query_text: str, top_k: int) -> list[dict]:
        """Return up to top_k nearest chunks as plain dicts with a 0-1 similarity score."""
        if self.count() == 0:
            return []

        result = self._collection.query(
            query_texts=[query_text],
            n_results=min(top_k, self.count()),
        )

        matches = []
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            matches.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "score": max(0.0, 1.0 - distance),
                    **metadata,
                }
            )
        return matches


@lru_cache
def get_vector_store(persist_directory: str, collection_name: str) -> VectorStore:
    """Cached so repeated requests reuse one Chroma client/collection."""
    return VectorStore(persist_directory=persist_directory, collection_name=collection_name)
