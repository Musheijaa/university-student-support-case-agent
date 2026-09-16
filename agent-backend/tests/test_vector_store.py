"""Exercises the real Chroma + embedding function against a throwaway
persist directory. No network call is needed once the default embedding
model is cached locally (see agent-backend/README.md), but this test is
slower than the pure-unit tests since it runs real embedding inference.
"""

from rag.chunker import Chunk
from rag.vector_store import VectorStore


def _chunk(chunk_id, document_id, page, text):
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name=f"Document {document_id}",
        doc_type="Policy",
        version_or_date="2024",
        source_filename=f"{document_id}.pdf",
        page=page,
        chunk_index=0,
        text=text,
    )


def test_ingest_and_query_round_trip(tmp_path):
    store = VectorStore(persist_directory=str(tmp_path), collection_name="test_collection")

    chunks = [
        _chunk("c1", "DOC001", 1, "Examination malpractice includes impersonation and cheating."),
        _chunk("c2", "DOC002", 5, "Tuition fees are payable at the start of each semester."),
    ]
    ingested = store.ingest(chunks)

    assert ingested == 2
    assert store.count() == 2

    results = store.query("What counts as examination malpractice?", top_k=2)
    assert len(results) == 2
    # the malpractice chunk should rank above the unrelated fees chunk
    assert results[0]["document_id"] == "DOC001"
    assert 0.0 <= results[0]["score"] <= 1.0


def test_query_against_empty_collection_returns_no_matches(tmp_path):
    store = VectorStore(persist_directory=str(tmp_path), collection_name="empty_collection")
    assert store.query("anything", top_k=4) == []


def test_ingest_is_idempotent_on_reingest(tmp_path):
    store = VectorStore(persist_directory=str(tmp_path), collection_name="reingest_collection")
    chunk = _chunk("c1", "DOC001", 1, "Some policy text.")

    store.ingest([chunk])
    store.ingest([chunk])  # re-ingesting the same chunk_id should upsert, not duplicate

    assert store.count() == 1
