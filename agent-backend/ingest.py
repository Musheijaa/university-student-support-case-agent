"""Builds/updates the RAG vector index from the controlled corpus.

Run this whenever the corpus changes. It re-extracts text from every
registered PDF, re-chunks it, and upserts the chunks into the persistent
Chroma collection - safe to re-run (chunk IDs are deterministic, so
re-ingesting the same corpus overwrites the same chunks rather than
duplicating them).

Usage (from agent-backend/, with dependencies installed):
    python ingest.py
"""

import sys

from config import get_settings
from rag.chunker import chunk_pages
from rag.corpus_manifest import CORPUS_MANIFEST
from rag.loader import load_corpus
from rag.vector_store import get_vector_store


def main() -> None:
    settings = get_settings()

    print(f"Loading corpus from {settings.rag_corpus_dir} ...")
    try:
        pages = load_corpus(settings.rag_corpus_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if not pages:
        print("WARNING: no extractable pages found - check the corpus directory and manifest.")
        sys.exit(1)

    print(f"Extracted {len(pages)} pages across the registered corpus.")

    pages_by_doc = {}
    for page in pages:
        pages_by_doc[page.document_id] = pages_by_doc.get(page.document_id, 0) + 1
    empty_docs = [doc for doc in CORPUS_MANIFEST if pages_by_doc.get(doc.id, 0) == 0]
    if empty_docs:
        print(
            f"WARNING: {len(empty_docs)} registered document(s) produced ZERO extractable "
            "pages (likely scanned/image-only PDFs with no text layer; this pipeline does "
            "not perform OCR). They are registered but not searchable until re-scanned or "
            "OCR'd:"
        )
        for doc in empty_docs:
            print(f"  - {doc.id}: {doc.filename}")

    chunks = chunk_pages(pages)
    print(f"Split into {len(chunks)} chunks.")

    vector_store = get_vector_store(
        persist_directory=settings.chroma_persist_directory,
        collection_name=settings.rag_collection_name,
    )
    ingested = vector_store.ingest(chunks)
    print(f"Ingested {ingested} chunks into '{settings.rag_collection_name}'.")
    print(f"Collection now holds {vector_store.count()} chunks total.")
    print(f"Persisted to: {settings.chroma_persist_directory}")


if __name__ == "__main__":
    main()
