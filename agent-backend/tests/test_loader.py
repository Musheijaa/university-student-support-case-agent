import pytest
from pypdf import PdfWriter

from rag.loader import load_corpus


def _write_blank_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        writer.write(f)


def test_missing_corpus_directory_raises():
    with pytest.raises(FileNotFoundError):
        load_corpus("/nonexistent/corpus/path")


def test_unregistered_file_is_skipped_without_error(tmp_path):
    # not in rag/corpus_manifest.py - must be skipped, not crash the ingestion run
    _write_blank_pdf(tmp_path / "not-in-the-manifest.pdf")
    pages = load_corpus(str(tmp_path))
    assert pages == []


def test_blank_page_with_no_text_is_skipped(tmp_path, monkeypatch):
    from rag import corpus_manifest

    fake_doc = corpus_manifest.CorpusDocument(
        id="DOCX",
        filename="blank.pdf",
        title="Blank Test Doc",
        doc_type="Policy",
        version_or_date="2024",
    )
    monkeypatch.setitem(corpus_manifest.CORPUS_BY_FILENAME, "blank.pdf", fake_doc)

    _write_blank_pdf(tmp_path / "blank.pdf")
    pages = load_corpus(str(tmp_path))
    assert pages == []
