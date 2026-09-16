# Corpus Source Register — Week 3 RAG

This registers every document in the Week 3 controlled corpus. Every
retrieved chunk carries its `document_id` (from this table) through the
whole RAG pipeline, so every answer's sources can be traced back to a
specific, identifiable document and page.

**Location:** `docs/makerereUniversityPolicyDocs/` (12 PDF files).
**Source type:** Public Makerere University policy/regulatory documents,
added to the repository by the project team. No private student data,
credentials, or confidential information is included.
**Manifest (single source of truth):** `agent-backend/rag/corpus_manifest.py`
— this table mirrors it for human readers.

| ID | Document | Type | Version/Date | Notes |
|---|---|---|---|---|
| DOC001 | Application Procedures and Requirements for Undergraduate Courses 2023-2024 | Admissions guide | 2023-2024 | |
| DOC002 | Approved Amended Rules on Examination Malpractices and Irregularities | Rules/regulations | March 2019 | |
| DOC003 | Guidelines for Field Attachment | Guidelines | Not specified in document | |
| DOC004 | Intellectual Property Management Policy | Policy | 2024 | |
| DOC005 | Joint Admissions Board Information Booklet 2026-2027 | Admissions booklet | 2026-2027 | |
| DOC006 | Makerere University College Statute 2026 | Statute | 2026 | |
| DOC007 | Makerere Mentorship Policy | Policy | June 2025 | |
| DOC008 | Makerere University Research Policy | Policy | Not specified in document | |
| DOC009 | Makerere University Research Policy (alternate copy) | Policy | Not specified in document | Filename suggests this may be a duplicate/alternate export of DOC008; kept as a separate ID pending confirmation, not auto-deduplicated |
| DOC015 | Makerere University Student Work Scheme Policy | Policy | Not specified in document | |
| DOC017 | Policy on Remarking Students' Work and Retention of Scripts | Policy | Not specified in document | |
| DOC018 | Rules Concerning Examination Malpractices (Staff) | Rules/regulations | Not specified in document | |

IDs are not contiguous (DOC010–DOC014 and DOC016 are missing) — see
"Removed documents" below. IDs are never reused once assigned, so a
retrieval result referencing an old ID in a log or evaluation record
still unambiguously identifies which document that was.

## Removed documents (2026-09-16)

Six of the original 18 corpus PDFs were **removed from the repository**
(`docs/makerereUniversityPolicyDocs/`) and unregistered from the
manifest, because they were scanned/image-based PDFs with **zero
extractable text** — confirmed by inspecting `pypdf`'s per-page
`extract_text()` output directly (0 characters from every page of every
one of these files). They contributed no chunks to the index and could
never be retrieved, so keeping them in the corpus directory was
misleading (they looked like part of the knowledge base but were
functionally invisible to the pipeline).

| Retired ID | Filename | Title |
|---|---|---|
| DOC010 | Mak-Fees-Policy-2016.pdf | Makerere Fees Policy |
| DOC011 | Mak-Grants-Administration-and-Management-Policy.pdf | Grants Administration and Management Policy |
| DOC012 | Makerere-Revised-Regulations-Semester-Credit-for-Undergraduates.pdf | Revised Regulations Governing the Semester Credit System for Undergraduates |
| DOC013 | Makerere-Students-Accommodation-Policy.pdf | Makerere Students' Accommodation Policy |
| DOC014 | Makerere-Teaching-and-Learning-Policy-Sept-2024.pdf | Makerere Teaching and Learning Policy |
| DOC016 | Open-Distance-eLearning-Policy.pdf | Open, Distance and eLearning (ODeL) Policy |

These files are still recoverable from git history (they were removed
via `git rm`, not deleted outside version control) if a re-scanned or
OCR'd version becomes available later. Re-adding a document that covers
the same topic should get a **new** DOC### id rather than reusing one
of these retired ones (see the note in `corpus_manifest.py`).

Notably, DOC010 was the university's dedicated **Fees Policy** — its
removal means the corpus currently has no readable source for
fees/tuition questions. Confirmed live: asking "What is the tuition
fees refund policy?" correctly returns "the documents provided do not
contain any information about a tuition-fees refund policy" rather than
an invented answer, but this is a real coverage gap, not just a
formatting one. Adding OCR (e.g. `pytesseract` + `pdf2image`) is a
reasonable way to recover these six documents in a later phase.

## Corpus statistics (as of last ingestion run)

- 12 documents registered and searchable
- 263 pages of extractable text (unchanged — the removed documents
  never contributed pages, since they had none extractable)
- 612 chunks indexed (1000-char chunks, 150-char overlap, chunked
  within page boundaries so page numbers stay exact)
