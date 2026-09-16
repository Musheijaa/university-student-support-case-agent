from rag.context_builder import NO_EVIDENCE_TEXT, build_evidence_block, build_sources
from rag.retriever import RetrievedChunk


def _chunk(document_id="DOC001", document_name="Fees Policy", page=3, score=0.8, text="evidence text"):
    return RetrievedChunk(
        text=text,
        score=score,
        document_id=document_id,
        document_name=document_name,
        doc_type="Policy",
        version_or_date="2016",
        page=page,
    )


def test_empty_chunks_produce_no_evidence_message():
    assert build_evidence_block([]) == NO_EVIDENCE_TEXT
    assert build_sources([]) == []


def test_evidence_block_includes_document_and_page_and_text():
    block = build_evidence_block([_chunk()])
    assert "[Document: Fees Policy]" in block
    assert "[Page: 3]" in block
    assert "evidence text" in block


def test_evidence_block_separates_multiple_chunks():
    block = build_evidence_block([_chunk(page=1), _chunk(page=2)])
    assert block.count("[Document: Fees Policy]") == 2
    assert "---" in block


def test_sources_are_deduplicated_by_document_and_page():
    chunks = [
        _chunk(document_id="DOC001", page=3),
        _chunk(document_id="DOC001", page=3),  # duplicate chunk from the same page
        _chunk(document_id="DOC001", page=4),
    ]
    sources = build_sources(chunks)
    assert len(sources) == 2
    assert (sources[0].document_id, sources[0].page) == ("DOC001", 3)
    assert (sources[1].document_id, sources[1].page) == ("DOC001", 4)


def test_sources_never_fabricate_a_page_number():
    # every Source field comes straight from the retrieved chunk's own metadata
    sources = build_sources([_chunk(document_id="DOC005", document_name="Handbook", page=12)])
    assert sources[0].document_id == "DOC005"
    assert sources[0].document == "Handbook"
    assert sources[0].page == 12
