from rag.retriever import RetrievedChunk, retrieve


class FakeVectorStore:
    """Duck-typed stand-in for VectorStore - no real Chroma/embedding involved."""

    def __init__(self, matches):
        self._matches = matches
        self.last_query = None

    def query(self, query_text, top_k):
        self.last_query = (query_text, top_k)
        return self._matches[:top_k]


def _match(document_id="DOC001", page=1, score=0.8, text="matched text"):
    return {
        "chunk_id": f"{document_id}-p{page}-c0",
        "text": text,
        "score": score,
        "document_id": document_id,
        "document_name": "Test Doc",
        "doc_type": "Policy",
        "version_or_date": "2024",
        "page": page,
    }


def test_retrieve_returns_typed_chunks():
    store = FakeVectorStore([_match()])
    results = retrieve(store, "some question", top_k=4)
    assert results == [
        RetrievedChunk(
            text="matched text",
            score=0.8,
            document_id="DOC001",
            document_name="Test Doc",
            doc_type="Policy",
            version_or_date="2024",
            page=1,
        )
    ]


def test_retrieve_passes_through_question_and_top_k():
    store = FakeVectorStore([_match()])
    retrieve(store, "when is registration?", top_k=7)
    assert store.last_query == ("when is registration?", 7)


def test_retrieve_filters_below_min_score():
    store = FakeVectorStore([_match(score=0.9), _match(score=0.1)])
    results = retrieve(store, "q", top_k=4, min_score=0.5)
    assert len(results) == 1
    assert results[0].score == 0.9


def test_retrieve_empty_matches_means_no_evidence():
    store = FakeVectorStore([])
    assert retrieve(store, "unanswerable question", top_k=4) == []
