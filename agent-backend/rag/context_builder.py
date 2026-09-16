"""Turns retrieved chunks into the prompt's evidence block and API sources.

Two separate outputs, built from the same retrieval results:
  - `build_evidence_block`: text handed to the LLM as part of the prompt.
  - `build_sources`: structured source list returned by the API, built
    directly from retrieval metadata so the model can never fabricate a
    citation that doesn't correspond to something actually retrieved.
"""

from dataclasses import dataclass

from rag.retriever import RetrievedChunk

NO_EVIDENCE_TEXT = "No sufficiently relevant sources were found in the corpus for this question."


@dataclass(frozen=True)
class Source:
    document_id: str
    document: str
    page: int


def build_evidence_block(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return NO_EVIDENCE_TEXT

    parts = []
    for chunk in chunks:
        parts.append(
            f"[Document: {chunk.document_name}]\n"
            f"[Page: {chunk.page}]\n\n"
            f"{chunk.text}"
        )
    return "\n\n---\n\n".join(parts)


def build_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    """Deduplicated source list, in order of first (highest-relevance) appearance."""
    seen: set[tuple[str, int]] = set()
    sources: list[Source] = []
    for chunk in chunks:
        key = (chunk.document_id, chunk.page)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            Source(document_id=chunk.document_id, document=chunk.document_name, page=chunk.page)
        )
    return sources
