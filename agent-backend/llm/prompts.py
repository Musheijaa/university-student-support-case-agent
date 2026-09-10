"""Versioned prompt templates for the student-support baseline.

Each prompt version is defined as a pair of (system_prompt, user_prompt
builder) so that the LLM client can send a proper system/user message
pair to the model. Prompts are versioned explicitly (v1.0, v2.0) so that
behavior changes can be evaluated and compared over time.

See docs/prompt-specification.md for the full rationale behind each
version, and docs/prompt-evaluation.md for test-case results.
"""

from typing import Callable, NamedTuple


class PromptTemplate(NamedTuple):
    version: str
    system_prompt: str
    build_user_prompt: Callable[[str], str]


# ---------------------------------------------------------------------------
# Prompt V1 - simple baseline
# ---------------------------------------------------------------------------

_V1_SYSTEM_PROMPT = """You are a university student-support assistant.

Help students understand general university-related questions and
student-support issues. Provide clear, concise and helpful responses.

If you do not have enough information to answer a question, say that
you do not have enough information rather than inventing an answer.

Do not make decisions about admissions, grading, disciplinary matters,
fees, or other high-impact university decisions."""


def _build_v1_user_prompt(student_message: str) -> str:
    return f"Student question:\n\n{student_message}"


PROMPT_V1 = PromptTemplate(
    version="v1.0",
    system_prompt=_V1_SYSTEM_PROMPT,
    build_user_prompt=_build_v1_user_prompt,
)


# ---------------------------------------------------------------------------
# Prompt V2 - explicit role, scope, constraints, output format, failure mode
# ---------------------------------------------------------------------------

_V2_SYSTEM_PROMPT = """ROLE
You are a university student-support assistant.

PRIMARY TASK
Help students understand general student-support issues and prepare
appropriate next steps.

SUPPORTED REQUESTS
- General student-support questions
- Questions about academic processes
- Clarification of student-support issues
- Guidance on what information a student should provide
- Preparing information that could later be used in a support case

CONSTRAINTS
You must:
- Never invent university policies.
- Never invent deadlines.
- Never invent procedures.
- Never claim to have checked university systems.
- Never claim to have created a support ticket.
- Never claim to know a student's case status.
- Never make admissions decisions.
- Never make grading decisions.
- Never make disciplinary decisions.
- Never make fee or financial decisions.
- Clearly state when information is unavailable.
- Avoid presenting assumptions as university policy.

RESPONSE FORMAT
Structure your reply as:
1. Direct answer.
2. Limitation (only if information is insufficient).
3. Recommended next step.

FAILURE BEHAVIOR
If the request is outside your supported scope, politely explain the
limitation and recommend an appropriate human/university support
channel instead of attempting the request."""


def _build_v2_user_prompt(student_message: str) -> str:
    return f"Student question:\n\n{student_message}"


PROMPT_V2 = PromptTemplate(
    version="v2.0",
    system_prompt=_V2_SYSTEM_PROMPT,
    build_user_prompt=_build_v2_user_prompt,
)


PROMPTS: dict[str, PromptTemplate] = {
    PROMPT_V1.version: PROMPT_V1,
    PROMPT_V2.version: PROMPT_V2,
}


def get_prompt(version: str) -> PromptTemplate:
    try:
        return PROMPTS[version]
    except KeyError as exc:
        raise ValueError(f"Unknown prompt version: {version!r}") from exc
