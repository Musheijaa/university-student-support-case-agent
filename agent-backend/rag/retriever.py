"""Semantic retrieval: student question -> ranked, relevant evidence chunks.

Retrieval results are never hidden from the rest of the system - they
are what `context_builder.py` turns into the prompt's evidence block and
what the API's `sources` field is built from directly, so nothing here
is LLM-generated.
"""

from dataclasses import dataclass

from rag.vector_store import VectorStore


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    score: float
    document_id: str
    document_name: str
    doc_type: str
    version_or_date: str
    page: int


def retrieve(
    vector_store: VectorStore,
    question: str,
    top_k: int,
    min_score: float = 0.0,
) -> list[RetrievedChunk]:
    """Return up to top_k chunks relevant to `question`, above `min_score`.

    An empty list means "no sufficiently relevant evidence was found" -
    callers must treat that as a signal the question may be unanswerable
    from the corpus, not retry with a lower bar.
    """
    raw_matches = vector_store.query(query_text=question, top_k=top_k)

    results = []
    for match in raw_matches:
        if match["score"] < min_score:
            continue
        results.append(
            RetrievedChunk(
                text=match["text"],
                score=match["score"],
                document_id=match["document_id"],
                document_name=match["document_name"],
                doc_type=match["doc_type"],
                version_or_date=match["version_or_date"],
                page=match["page"],
            )
        )
    return results
