"""Loads controlled-corpus PDFs and extracts text with page-level metadata.

Each page of each PDF becomes one `LoadedPage`, tagged with the stable
document_id from `corpus_manifest.py` so provenance survives every later
step (chunking, embedding, retrieval, source attribution).
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from rag.corpus_manifest import CORPUS_BY_FILENAME

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedPage:
    document_id: str
    document_name: str
    doc_type: str
    version_or_date: str
    source_filename: str
    page: int
    text: str


def load_corpus(corpus_dir: str) -> list[LoadedPage]:
    """Extract text per page from every registered PDF in `corpus_dir`.

    Files present on disk but missing from CORPUS_BY_FILENAME are skipped
    with a warning rather than silently ingested with no provenance -
    every ingested document must have a stable ID from the source register.
    """
    corpus_path = Path(corpus_dir)
    if not corpus_path.is_dir():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_path}")

    pages: list[LoadedPage] = []
    for pdf_path in sorted(corpus_path.glob("*.pdf")):
        manifest_entry = CORPUS_BY_FILENAME.get(pdf_path.name)
        if manifest_entry is None:
            logger.warning(
                "Skipping %s: not registered in rag/corpus_manifest.py "
                "(add it with a stable DOC### id before ingesting).",
                pdf_path.name,
            )
            continue

        reader = PdfReader(str(pdf_path))
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            pages.append(
                LoadedPage(
                    document_id=manifest_entry.id,
                    document_name=manifest_entry.title,
                    doc_type=manifest_entry.doc_type,
                    version_or_date=manifest_entry.version_or_date,
                    source_filename=manifest_entry.filename,
                    page=page_number,
                    text=text,
                )
            )

    return pages
