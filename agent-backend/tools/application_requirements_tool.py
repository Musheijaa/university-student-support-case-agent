"""Tool 5: ApplicationRequirementsTool.

Queries the official Makerere University Application Procedures and Requirements for
Undergraduate Courses (2023-2024) document (DOC001) under makerereUniversityPolicyDocs,
searches for matching requirements, eligibility criteria, application steps, and fees,
and prompts the LLM to synthesize a grounded, page-cited response.
"""

import logging
from pathlib import Path
import re
from typing import Any, Callable

from pypdf import PdfReader

from config import get_settings
from llm.client import GroqClient, LLMConfigurationError, LLMRequestError
from tools.base import BaseTool
from tools.schemas import (
    ApplicationRequirementsInput,
    ApplicationRequirementsOutput,
    DocumentExcerpt,
)

logger = logging.getLogger(__name__)

DOCUMENT_ID = "DOC001"
DOCUMENT_FILENAME = "Application-Procedures-Requirements-Undergraduate-Courses2023-2024.pdf"
DOCUMENT_TITLE = "Application Procedures and Requirements for Undergraduate Courses 2023-2024"

# Common stopwords to exclude from pure keyword scoring
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "with", "at",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am",
    "how", "can", "could", "should", "would", "may", "might", "must", "i",
    "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "their", "our", "its", "need", "tell", "give", "please",
}


class ApplicationRequirementsTool(
    BaseTool[ApplicationRequirementsInput, ApplicationRequirementsOutput]
):
    """Tool to search the Application Procedures & Requirements document and prompt the LLM."""

    name = "search_application_requirements"
    description = (
        "Retrieves and analyzes official procedures, requirements, eligibility criteria, "
        "admission guidelines, fees, and subject combinations from the Makerere University "
        "Application Procedures & Requirements for Undergraduate Courses document using AI search and synthesis."
    )
    input_schema_class = ApplicationRequirementsInput
    output_schema_class = ApplicationRequirementsOutput

    def __init__(
        self,
        llm_client: Any | None = None,
        custom_pdf_path: str | Path | None = None,
    ) -> None:
        """Initialize tool with optional injected LLM client or custom PDF path.

        Args:
            llm_client: Optional object implementing `generate(system_prompt, user_prompt) -> str`
            custom_pdf_path: Optional explicit path to the PDF document.
        """
        self._llm_client = llm_client
        self._custom_pdf_path = Path(custom_pdf_path) if custom_pdf_path else None
        self._cached_pages: list[tuple[int, str]] | None = None

    def authorize(self, input_data: ApplicationRequirementsInput) -> tuple[bool, str]:
        """Verify student or agent credentials."""
        token = input_data.auth_token.strip().lower()
        if token in {"unauthorized", "expired", "invalid", "revoked", "forbidden"}:
            return False, f"Auth token '{input_data.auth_token}' is invalid or expired."
        if token.startswith("invalid-") or token.startswith("unauthorized-"):
            return False, "Provided credentials do not have permission to query admissions documents."
        return True, "Authorization successful."

    def _resolve_pdf_path(self) -> Path | None:
        """Find the PDF document on disk using multiple candidate locations."""
        if self._custom_pdf_path and self._custom_pdf_path.is_file():
            return self._custom_pdf_path

        settings = get_settings()
        candidates = [
            Path(settings.rag_corpus_dir) / DOCUMENT_FILENAME,
            Path("docs/makerereUniversityPolicyDocs") / DOCUMENT_FILENAME,
            Path("../docs/makerereUniversityPolicyDocs") / DOCUMENT_FILENAME,
            Path(__file__).resolve().parent.parent.parent
            / "docs"
            / "makerereUniversityPolicyDocs"
            / DOCUMENT_FILENAME,
        ]

        for path in candidates:
            try:
                resolved = path.resolve()
                if resolved.is_file():
                    return resolved
            except Exception:
                continue

        return None

    def _load_pages(self, pdf_path: Path) -> list[tuple[int, str]]:
        """Extract and cache text per page from the PDF document."""
        if self._cached_pages is not None:
            return self._cached_pages

        reader = PdfReader(str(pdf_path))
        pages: list[tuple[int, str]] = []
        for idx, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append((idx, text))

        self._cached_pages = pages
        return pages

    def _search_pages(
        self,
        pages: list[tuple[int, str]],
        query: str,
        course_code: str | None,
        applicant_category: str | None,
        top_k: int,
    ) -> list[DocumentExcerpt]:
        """Rank and return the top_k most relevant document pages with score attribution."""
        # Normalize search terms
        query_lower = query.lower()
        query_words = [
            w for w in re.findall(r"\b\w+\b", query_lower)
            if w not in STOPWORDS and len(w) > 2
        ]

        course_code_clean = course_code.strip().upper() if course_code else None
        category_clean = applicant_category.strip().lower() if applicant_category else None

        scored_pages: list[tuple[float, int, str]] = []

        for page_num, text in pages:
            if not text:
                continue
            text_lower = text.lower()
            score = 0.0

            # 1. Exact query phrase match
            if len(query_words) > 1 and query_lower in text_lower:
                score += 15.0

            # 2. Individual query term matches
            for word in query_words:
                count = text_lower.count(word)
                if count > 0:
                    score += min(count, 5) * 1.5

            # 3. Course code filter / boost
            if course_code_clean:
                # Look for exact word boundary match for course code (e.g. \bBSW\b or \bCSC\b)
                if re.search(rf"\b{re.escape(course_code_clean)}\b", text, re.IGNORECASE):
                    score += 20.0

            # 4. Applicant category filter / boost
            if category_clean:
                if category_clean in text_lower:
                    score += 8.0
                cat_tokens = [t for t in category_clean.split() if t not in STOPWORDS]
                for ct in cat_tokens:
                    if ct in text_lower:
                        score += 3.0

            # 5. Domain concept boosts
            if any(term in query_lower for term in ["fee", "cost", "pay", "shs", "dollar", "bank", "prn"]):
                if any(k in text_lower for k in ["application fee", "sh.52, 000", "50,000", "pay.mak.ac.ug", "prn"]):
                    score += 10.0

            if any(term in query_lower for term in ["procedure", "apply", "step", "online", "portal"]):
                if any(k in text_lower for k in ["applications.mak.ac.ug", "online application", "procedure"]):
                    score += 10.0

            if any(term in query_lower for term in ["requirement", "essential", "relevant", "desirable", "weight"]):
                if any(k in text_lower for k in ["essential", "relevant", "desirable", "weighting"]):
                    score += 6.0

            if score > 0:
                scored_pages.append((score, page_num, text))

        # Sort descending by score
        scored_pages.sort(key=lambda x: x[0], reverse=True)

        # Fallback if no specific keywords matched: provide foundational pages (pages 1, 2, 3)
        if not scored_pages:
            selected_raw = pages[:min(top_k, len(pages))]
            return [
                DocumentExcerpt(
                    page=p_num,
                    text=p_text[:1500],
                    relevance_score=0.1,
                )
                for p_num, p_text in selected_raw if p_text
            ]

        # Take top_k pages
        top_matches = scored_pages[:top_k]
        return [
            DocumentExcerpt(
                page=p_num,
                text=p_text[:2000],  # Bound length for LLM context window safety
                relevance_score=round(score, 3),
            )
            for score, p_num, p_text in top_matches
        ]

    def _build_llm_prompts(
        self,
        query: str,
        excerpts: list[DocumentExcerpt],
        course_code: str | None,
        applicant_category: str | None,
    ) -> tuple[str, str]:
        """Construct system and user prompts for the LLM."""
        system_prompt = (
            "You are the Makerere University Academic Registrar Admissions Consultant.\n"
            "Your objective is to provide an accurate, clear, and comprehensive answer to the user's "
            "inquiry regarding university application procedures, entry requirements, fees, and guidelines.\n\n"
            "STRICT CONSTRAINTS:\n"
            "1. Base your response EXCLUSIVELY on the provided excerpts from the official Makerere University "
            "document: 'Application Procedures and Requirements for Undergraduate Courses 2023-2024' (DOC001).\n"
            "2. Always cite the exact page number(s) (e.g. [Page 2], [Page 7]) where each requirement, fee, "
            "or process step is found.\n"
            "3. If detailing course requirements, clearly list Essential, Relevant, and Desirable subjects with their "
            "weighting rules where applicable.\n"
            "4. If detailing application procedures or fees, specify the official portal (applications.mak.ac.ug or pay.mak.ac.ug) "
            "and payment instructions via URA PRN as recorded in the document.\n"
            "5. If the excerpts do not contain the answer, explicitly state that the specific details are not found in this document "
            "and direct the applicant to contact the Academic Registrar (ar@mak.ac.ug)."
        )

        evidence_blocks = []
        for exc in excerpts:
            evidence_blocks.append(f"--- [Page {exc.page}] ---\n{exc.text}")

        evidence_str = "\n\n".join(evidence_blocks)

        user_prompt = (
            f"OFFICIAL DOCUMENT EXCERPTS (DOC001: {DOCUMENT_TITLE}):\n\n"
            f"{evidence_str}\n\n"
            f"USER INQUIRY:\n"
            f"{query}\n"
            f"- Applicant Category: {applicant_category or 'General / Not specified'}\n"
            f"- Target Course Code: {course_code or 'None specified'}\n\n"
            "Please search through the excerpts above and synthesize a comprehensive, well-structured response with page citations."
        )

        return system_prompt, user_prompt

    def _synthesize_offline_response(
        self,
        query: str,
        excerpts: list[DocumentExcerpt],
        course_code: str | None,
        applicant_category: str | None,
    ) -> str:
        """Grounded synthesis fallback when external LLM provider is not configured or offline."""
        pages_cited = ", ".join(f"Page {e.page}" for e in excerpts)
        lines = [
            f"According to the Makerere University Application Procedures & Requirements for Undergraduate Courses (DOC001, {pages_cited}):\n"
        ]

        for exc in excerpts:
            cleaned_snippet = " ".join(exc.text.split())
            if len(cleaned_snippet) > 400:
                cleaned_snippet = cleaned_snippet[:400] + "..."
            lines.append(f"• [Page {exc.page}]: {cleaned_snippet}\n")

        lines.append(
            "\nKey Guidance & Procedures:"
            "\n1. Application Portal: Online applications must be submitted via applications.mak.ac.ug."
            "\n2. Payment: Fees must be paid through any URA-designated commercial bank using a Payment Reference Number (PRN) generated from pay.mak.ac.ug."
            "\n3. Inquiries: For questions not resolved in this guide, contact the Academic Registrar at ar@mak.ac.ug."
            "\n\n*(Note: LLM provider is currently unconfigured; information presented is extracted directly from official document text)*"
        )
        return "\n".join(lines)

    def _run(self, input_data: ApplicationRequirementsInput) -> ApplicationRequirementsOutput:
        """Execute document retrieval, scoring, and LLM synthesis."""
        pdf_path = self._resolve_pdf_path()
        if not pdf_path:
            return self._handle_doc_not_found()

        try:
            pages = self._load_pages(pdf_path)
        except Exception as exc:
            return self._handle_execution_error(
                Exception(f"Failed to read PDF document '{DOCUMENT_FILENAME}': {exc}")
            )

        # Retrieve top relevant pages
        top_excerpts = self._search_pages(
            pages=pages,
            query=input_data.query,
            course_code=input_data.course_code,
            applicant_category=input_data.applicant_category,
            top_k=input_data.top_k_pages,
        )

        relevant_pages = sorted(list({exc.page for exc in top_excerpts}))
        system_prompt, user_prompt = self._build_llm_prompts(
            query=input_data.query,
            excerpts=top_excerpts,
            course_code=input_data.course_code,
            applicant_category=input_data.applicant_category,
        )

        # Generate response via LLM
        settings = get_settings()
        response_text: str

        if self._llm_client is not None:
            # Injected client (e.g. mock or custom provider)
            try:
                response_text = self._llm_client.generate(
                    system_prompt=system_prompt, user_prompt=user_prompt
                )
            except Exception as exc:
                logger.warning("Injected LLM client failed, falling back to grounded extraction: %s", exc)
                response_text = self._synthesize_offline_response(
                    query=input_data.query,
                    excerpts=top_excerpts,
                    course_code=input_data.course_code,
                    applicant_category=input_data.applicant_category,
                )
        elif settings.groq_configured:
            # Production Groq client
            try:
                client = GroqClient(
                    api_key=settings.groq_api_key,
                    model=settings.groq_model,
                )
                response_text = client.generate(
                    system_prompt=system_prompt, user_prompt=user_prompt
                )
            except (LLMConfigurationError, LLMRequestError) as exc:
                logger.warning("Groq generation failed (%s), using grounded fallback.", exc)
                response_text = self._synthesize_offline_response(
                    query=input_data.query,
                    excerpts=top_excerpts,
                    course_code=input_data.course_code,
                    applicant_category=input_data.applicant_category,
                )
        else:
            # Offline / unconfigured environment
            response_text = self._synthesize_offline_response(
                query=input_data.query,
                excerpts=top_excerpts,
                course_code=input_data.course_code,
                applicant_category=input_data.applicant_category,
            )

        return ApplicationRequirementsOutput(
            success=True,
            status="SUCCESS",
            query=input_data.query,
            response=response_text,
            document_title=DOCUMENT_TITLE,
            document_id=DOCUMENT_ID,
            relevant_pages=relevant_pages,
            extracted_excerpts=top_excerpts,
            message=(
                f"Successfully searched {DOCUMENT_TITLE} and generated response "
                f"grounded in {len(relevant_pages)} page(s) ({', '.join(str(p) for p in relevant_pages)})."
            ),
            error=None,
        )

    def _handle_doc_not_found(self) -> ApplicationRequirementsOutput:
        return ApplicationRequirementsOutput(
            success=False,
            status="DOCUMENT_NOT_FOUND",
            query="",
            response="",
            document_title=DOCUMENT_TITLE,
            document_id=DOCUMENT_ID,
            relevant_pages=[],
            extracted_excerpts=[],
            message=(
                f"Document '{DOCUMENT_FILENAME}' could not be located in policy docs directories."
            ),
            error="DOC_NOT_FOUND",
        )

    def _handle_validation_error(self, error_msg: str) -> ApplicationRequirementsOutput:
        return ApplicationRequirementsOutput(
            success=False,
            status="INVALID_INPUT",
            query="",
            response="",
            document_title=DOCUMENT_TITLE,
            document_id=DOCUMENT_ID,
            relevant_pages=[],
            extracted_excerpts=[],
            message="Failed to query application requirements due to invalid or missing parameters.",
            error=f"VALIDATION_ERROR: {error_msg}",
        )

    def _handle_authorization_failure(self, reason: str) -> ApplicationRequirementsOutput:
        return ApplicationRequirementsOutput(
            success=False,
            status="UNAUTHORIZED",
            query="",
            response="",
            document_title=DOCUMENT_TITLE,
            document_id=DOCUMENT_ID,
            relevant_pages=[],
            extracted_excerpts=[],
            message="Application requirements query unauthorized.",
            error=f"AUTH_DENIED: {reason}",
        )

    def _handle_execution_error(self, exc: Exception) -> ApplicationRequirementsOutput:
        return ApplicationRequirementsOutput(
            success=False,
            status="SERVICE_ERROR",
            query="",
            response="",
            document_title=DOCUMENT_TITLE,
            document_id=DOCUMENT_ID,
            relevant_pages=[],
            extracted_excerpts=[],
            message="An unexpected system error occurred while searching application requirements.",
            error=f"EXECUTION_ERROR: {str(exc)}",
        )
