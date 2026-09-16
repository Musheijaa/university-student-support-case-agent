from rag.chunker import chunk_pages
from rag.loader import LoadedPage


def _page(text: str, page_number: int = 1) -> LoadedPage:
    return LoadedPage(
        document_id="DOC001",
        document_name="Test Document",
        doc_type="Policy",
        version_or_date="2024",
        source_filename="test.pdf",
        page=page_number,
        text=text,
    )


def test_short_page_produces_a_single_chunk():
    chunks = chunk_pages([_page("short text")], chunk_size=1000, overlap=150)
    assert len(chunks) == 1
    assert chunks[0].text == "short text"


def test_long_page_is_split_with_overlap():
    text = "a" * 2500
    chunks = chunk_pages([_page(text)], chunk_size=1000, overlap=150)
    assert len(chunks) == 3
    # consecutive chunks overlap by the configured amount
    assert chunks[0].text[-150:] == chunks[1].text[:150]


def test_chunk_metadata_is_preserved_from_page():
    chunks = chunk_pages([_page("some text", page_number=23)])
    chunk = chunks[0]
    assert chunk.document_id == "DOC001"
    assert chunk.document_name == "Test Document"
    assert chunk.page == 23


def test_chunk_ids_are_unique_and_traceable():
    text = "b" * 2500
    chunks = chunk_pages([_page(text, page_number=5)])
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(cid.startswith("DOC001-p5-c") for cid in ids)


def test_chunking_never_crosses_a_page_boundary():
    pages = [_page("first page text", page_number=1), _page("second page text", page_number=2)]
    chunks = chunk_pages(pages)
    assert {c.page for c in chunks if "first" in c.text} == {1}
    assert {c.page for c in chunks if "second" in c.text} == {2}
