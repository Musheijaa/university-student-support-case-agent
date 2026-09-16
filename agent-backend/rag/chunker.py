"""Splits loaded pages into overlapping text chunks, keeping metadata attached.

Chunking happens within a single page's text (never across pages), so a
chunk's page number is always exact rather than approximate.
"""

from dataclasses import dataclass

from rag.loader import LoadedPage

CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    document_name: str
    doc_type: str
    version_or_date: str
    source_filename: str
    page: int
    chunk_index: int
    text: str


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    pieces = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        pieces.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return pieces


def chunk_pages(
    pages: list[LoadedPage],
    chunk_size: int = CHUNK_SIZE_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        pieces = _split_text(page.text, chunk_size, overlap)
        for chunk_index, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}-p{page.page}-c{chunk_index}",
                    document_id=page.document_id,
                    document_name=page.document_name,
                    doc_type=page.doc_type,
                    version_or_date=page.version_or_date,
                    source_filename=page.source_filename,
                    page=page.page,
                    chunk_index=chunk_index,
                    text=piece,
                )
            )
    return chunks
