# RAG Retrieval/Grounding Failures — Week 3

Four real failures, found by actually running the pipeline against the
live corpus and Groq API (see `docs/rag-evaluation.md` for the full
15-case run these were drawn from). None of these are hypothetical —
each includes the actual retrieved scores or text that demonstrates it.

None of these caused a hallucinated or unsafe final answer — the
`rag-v1.0` prompt's "don't invent, say so if insufficient" instruction
held up in every case. They are still real weaknesses in the pipeline's
retrieval precision and corpus quality, worth fixing before Week 4.

---

## F1 — Corpus coverage gap: 6 documents are unreadable, no OCR

**Category:** insufficient evidence (entire documents unavailable)

**Question:** "What is the tuition fees refund policy for a student who withdraws mid-semester?" (RAG-06), and any question about accommodation (RAG-13) or online/distance learning exams (RAG-14).

**Expected behavior:** Answer from the university's actual Fees / Accommodation / ODeL policies.

**Actual behavior:** Correctly declined rather than inventing an answer — but only because there is *no* readable source at all, not because retrieval reasoned well over real content.

**Retrieved chunks:** None from the actually-relevant document, because it was never ingested — no chunks for it exist in the index at all.

**Why retrieval/grounding failed:** `Mak-Fees-Policy-2016.pdf`, `Makerere-Students-Accommodation-Policy.pdf`, `Open-Distance-eLearning-Policy.pdf`, and 3 others are scanned/image-based PDFs. `pypdf.PdfReader.pages[i].extract_text()` returns 0 characters for every page of each — confirmed directly (see `docs/corpus-source-register.md`). `loader.py` correctly skips pages with empty text, so these documents silently contribute zero chunks.

**Root cause:** This pipeline extracts text only; it has no OCR step. A scanned PDF with no embedded text layer is invisible to it regardless of how relevant its content is.

**Potential improvement:** Add an OCR fallback (e.g. `pytesseract` + `pdf2image`, requiring a system Tesseract install) triggered when a PDF yields near-zero extracted characters, so these 6 documents (already removed from the corpus per this finding — see `docs/corpus-source-register.md`) could be re-added and actually retrieved. Flagged as a candidate for Week 4, not implemented now (adds a system-level dependency beyond this phase's scope).

---

## F2 — Retrieval surfaces topically-adjacent but substantively irrelevant sources for personal/off-corpus questions

**Category:** semantically similar but incorrect document / insufficient evidence disguised as a normal result

**Questions:** RAG-12 ("Has my lecturer approved my special examination request?"), RAG-13 (accommodation/hostel), RAG-14 (online/distance exam policy).

**Expected behavior:** If nothing genuinely relevant exists, retrieval should return nothing (or the `sources` list should be empty), matching what happened for RAG-11 and RAG-15.

**Actual behavior:** The model's prose answer was correct ("the documents don't contain this information"), but `sources` was *not* empty — it listed 3-4 documents with no real bearing on the question.

**Retrieved chunks (real scores, `RAG_MIN_SCORE=0.35`):**

| Query | Top scores returned |
|---|---|
| "Has my lecturer approved my special examination request?" | DOC002 p10 = 0.484, DOC017 p1 = 0.461, DOC002 p15 = 0.450, DOC018 p1 = 0.440 |
| "Accommodation policy / hostel application" | DOC015 p10 = 0.424, DOC015 p3 = 0.412, DOC006 p27 = 0.406, DOC001 p1 = 0.399 |
| "Online/distance learning exam policy" | DOC007 p16 = 0.529, DOC002 p3 = 0.523, DOC002 p2 = 0.518, DOC015 p3 = 0.509 |

**Why retrieval/grounding failed:** All of these scores clear the 0.35 threshold — some by a wide margin (0.53) — despite the retrieved text not actually answering the question. The shared surface vocabulary ("examination," "student," "university," "policy") is enough for the MiniLM embedding to place these chunks close to the query in vector space, even though the semantic content doesn't match. The threshold that correctly filters out clearly-unrelated content (e.g. RAG-11/RAG-15 scored below 0.35 and returned nothing) isn't strict enough to catch this more subtle, keyword-driven false positive.

**Root cause:** A single global similarity threshold can't distinguish "genuinely on-topic" from "shares vocabulary but is off-topic" — that distinction usually needs either a cross-encoder re-ranking step or a higher/adaptive threshold, neither of which this lightweight pipeline has.

**Potential improvement:** The model's own textual judgment is currently the real safety net here (and it worked), but the `sources` field should not silently show low-value matches as if they were solid grounding. Options for Week 4+: raise `RAG_MIN_SCORE` further and measure the trade-off against true positives like RAG-06/RAG-08 (which scored 0.37-0.42), or add a re-ranking step, or only surface a source in the API response if the model's answer text actually appears to draw on it.

---

## F3 — Duplicate document not deduplicated at ingestion

**Category:** insufficient metadata / corpus hygiene

**Question:** RAG-10, "What is the difference between the two Makerere University Research Policy documents?"

**Expected behavior:** N/A directly, but ideally the corpus wouldn't contain two IDs for the same content in the first place.

**Actual behavior:** The model itself discovered and correctly reported that DOC008 and DOC009's retrieved pages (1 and 4) are textually identical.

**Retrieved chunks:** DOC008 p1, DOC009 p1, DOC008 p4, DOC009 p4 — same text under two different `document_id`s.

**Why retrieval/grounding failed:** This isn't strictly a retrieval error (both documents *are* genuinely similar to the query), but it produces a misleading source list: a student sees "2 sources" confirming something, when there's really only 1 underlying document counted twice.

**Root cause:** `MAKERERE_UNIVERSITY_RESEARCH_POLICY.pdf` and `MAKERERE_UNIVERSITY_RESEARCH_POLICY_0.pdf` were registered as two separate corpus documents (DOC008/DOC009) during ingestion. The pipeline deduplicates by `chunk_id` (see `vector_store.py`'s `upsert`) but never checks whether two different source files contain the same content. This was already flagged as a suspected duplicate in `rag/corpus_manifest.py` before this evaluation ran; RAG-10's real output is independent confirmation.

**Potential improvement:** Add a content-hash check at ingestion time (e.g. hash each PDF's extracted text) and either merge duplicate documents under one ID or flag them for manual review before indexing.

---

## F4 — Fixed-size chunking truncates evidence mid-sentence

**Category:** chunk boundary / incomplete evidence

**Question:** RAG-04, "Who owns intellectual property created by a student while completing a thesis?"

**Expected behavior:** Complete, uncut evidence for the retrieved clause.

**Actual behavior:** The model answered correctly but explicitly noted: *"the policy text is cut off but indicates a similar condition"* — it recognized incomplete evidence and said so rather than guessing the missing part.

**Retrieved chunk (verbatim tail, DOC004 p20, score 0.677):**
```
the sponsoring body has not made any prior
declaration to the University in respect of the claim
to the intellectual property
6.2.4. The terms of the Research Contract shall regulate the
ownership of IP created by a Student in the course of
such Research Contract, as set out in Subsection 8.0.
```
and the preceding chunk from the same page ends:
```
(c) In the case of sponsored s
```
— cut off mid-word ("sponsored s[tudents]" or similar), splitting clause (c) of a lettered list across two chunks.

**Why retrieval/grounding failed:** `chunker.py` splits page text at a fixed character offset (1000 chars, 150-char overlap) with no awareness of sentence, clause, or list-item boundaries, so a chunk boundary can land in the middle of a legal sub-clause.

**Root cause:** Character-count chunking is simple and correctly keeps page-level metadata exact, but has no semantic awareness of where a "complete thought" ends.

**Potential improvement:** Move to sentence- or paragraph-aware chunking (e.g. split on sentence boundaries and pack up to the size limit, rather than cutting at a raw character offset), which would reduce mid-clause truncation like this. Not implemented now since it adds a text-segmentation dependency beyond this phase's minimal scope — flagged for a later pass over `rag/chunker.py`.

---

## Summary

| ID | Category | Caused unsafe output? | Status |
|---|---|---|---|
| F1 | Insufficient evidence (unreadable documents) | No — correctly declined | Root cause fixed by removing the 6 unreadable docs from the active corpus; OCR re-ingestion is a Week 4+ candidate |
| F2 | Semantically-adjacent-but-irrelevant retrieval | No — model's text stayed safe, but `sources` was misleading | Open — needs a stricter relevance signal (re-ranking or higher threshold) |
| F3 | Duplicate document, not deduplicated | No | Open — needs content-hash dedup at ingestion |
| F4 | Chunk-boundary truncation | No — model flagged the gap itself | Open — needs semantic-boundary-aware chunking |
