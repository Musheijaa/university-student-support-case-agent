"""Stable document-ID mapping for the controlled corpus.

This is the single source of truth linking each corpus file to a stable
DOC### ID and its provenance metadata. `docs/corpus-source-register.md`
mirrors this table for human readers; `loader.py` uses it directly so
every chunk (and therefore every retrieved source) can be traced back
to a specific, identifiable document.

Do not remove or renumber an existing ID once it has been used —
existing indexes/evaluation records would silently point at the wrong
document. DOC010, DOC011, DOC012, DOC013, DOC014, and DOC016 were
removed from both this manifest and the corpus directory on
2026-09-16: they were scanned/image-only PDFs with no extractable text
layer (confirmed via pypdf - 0 characters from every page), so they
never contributed a single chunk. Those IDs are retired, not reused,
in case they resurface in git history or old notes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CorpusDocument:
    id: str
    filename: str
    title: str
    doc_type: str
    version_or_date: str
    notes: str = ""


CORPUS_MANIFEST: list[CorpusDocument] = [
    CorpusDocument(
        id="DOC001",
        filename="Application-Procedures-Requirements-Undergraduate-Courses2023-2024.pdf",
        title="Application Procedures and Requirements for Undergraduate Courses 2023-2024",
        doc_type="Admissions guide",
        version_or_date="2023-2024",
    ),
    CorpusDocument(
        id="DOC002",
        filename="Approved-Amended-Rules-on-Examination-Malpractices-and-Irregularities-March-2019.pdf",
        title="Approved Amended Rules on Examination Malpractices and Irregularities",
        doc_type="Rules/regulations",
        version_or_date="March 2019",
    ),
    CorpusDocument(
        id="DOC003",
        filename="GUIDELINES_FOR_FIELD_ATTACHMENT.pdf",
        title="Guidelines for Field Attachment",
        doc_type="Guidelines",
        version_or_date="Not specified in document",
    ),
    CorpusDocument(
        id="DOC004",
        filename="Intellectual-Property-Management-Policy-2024.pdf",
        title="Intellectual Property Management Policy",
        doc_type="Policy",
        version_or_date="2024",
    ),
    CorpusDocument(
        id="DOC005",
        filename="Joint-Admissions-Board-Information-Booklet-2026-2027.pdf",
        title="Joint Admissions Board Information Booklet 2026-2027",
        doc_type="Admissions booklet",
        version_or_date="2026-2027",
    ),
    CorpusDocument(
        id="DOC006",
        filename="MAKERERE UNIVERSITY COLLEGE STATUTE 2026.pdf",
        title="Makerere University College Statute 2026",
        doc_type="Statute",
        version_or_date="2026",
    ),
    CorpusDocument(
        id="DOC007",
        filename="MAKERERE-MENTORSHIP-POLICY-JUNE-2025.pdf",
        title="Makerere Mentorship Policy",
        doc_type="Policy",
        version_or_date="June 2025",
    ),
    CorpusDocument(
        id="DOC008",
        filename="MAKERERE_UNIVERSITY_RESEARCH_POLICY.pdf",
        title="Makerere University Research Policy",
        doc_type="Policy",
        version_or_date="Not specified in document",
    ),
    CorpusDocument(
        id="DOC009",
        filename="MAKERERE_UNIVERSITY_RESEARCH_POLICY_0.pdf",
        title="Makerere University Research Policy (alternate copy)",
        doc_type="Policy",
        version_or_date="Not specified in document",
        notes="Filename suggests this may be a duplicate/alternate export of DOC008; kept as a separate source ID pending confirmation, not deduplicated automatically.",
    ),
    CorpusDocument(
        id="DOC015",
        filename="Makerere-University-Student-Work-Scheme-Policy.pdf",
        title="Makerere University Student Work Scheme Policy",
        doc_type="Policy",
        version_or_date="Not specified in document",
    ),
    CorpusDocument(
        id="DOC017",
        filename="Policy_on_remarking_students_work_and_retention_of_scripts.pdf",
        title="Policy on Remarking Students' Work and Retention of Scripts",
        doc_type="Policy",
        version_or_date="Not specified in document",
    ),
    CorpusDocument(
        id="DOC018",
        filename="Rules_concerning_Examination_Malpractices_staff.pdf",
        title="Rules Concerning Examination Malpractices (Staff)",
        doc_type="Rules/regulations",
        version_or_date="Not specified in document",
    ),
]

CORPUS_BY_FILENAME: dict[str, CorpusDocument] = {doc.filename: doc for doc in CORPUS_MANIFEST}
