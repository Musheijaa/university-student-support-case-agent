# Prompt Specification — Week 2 Baseline

This document specifies the prompt templates used by the Week 2
foundation-model baseline (`agent-backend/llm/prompts.py`). Both versions are sent
to the model as a system message plus a user message containing the
student's question.

## Version history

**V1.0** — Initial baseline prompt. Establishes the assistant's role, a
general instruction to avoid inventing answers, and a short list of
decisions the assistant must not make.

**V2.0** — Added explicit scope (supported request types), an expanded
and itemized safety-boundary list, a required response format, and
explicit failure behavior for out-of-scope requests. Currently the
active prompt version (see `Settings.active_prompt_version` in
`agent-backend/config.py`).

---

## Prompt V1.0

| Field | Value |
|---|---|
| Version | v1.0 |
| Role | University student-support assistant |
| Task | Answer general university/student-support questions |
| Context | None — foundation model only, no retrieval |
| Constraints | Must not invent information when insufficient context exists; must not decide on admissions, grading, discipline, or fees |
| Output format | Free-form prose |
| Failure behavior | Implicit — relies on the model saying "I don't have enough information" |
| Known limitations | No explicit output structure; no explicit instruction covering claims about system actions (e.g. "I checked the system") or ticket creation; safety boundaries are a flat list rather than itemized |

System prompt text:

```text
You are a university student-support assistant.

Help students understand general university-related questions and
student-support issues. Provide clear, concise and helpful responses.

If you do not have enough information to answer a question, say that
you do not have enough information rather than inventing an answer.

Do not make decisions about admissions, grading, disciplinary matters,
fees, or other high-impact university decisions.
```

---

## Prompt V2.0

| Field | Value |
|---|---|
| Version | v2.0 |
| Role | University student-support assistant |
| Task | Help students understand student-support issues and prepare appropriate next steps |
| Context | None — foundation model only, no retrieval (explicitly acknowledged in constraints) |
| Constraints | Itemized: no invented policies/deadlines/procedures; no claims of having checked systems, created tickets, or knowing case status; no admissions/grading/disciplinary/fee decisions; must state when information is unavailable |
| Output format | Structured: (1) direct answer, (2) limitation if information is insufficient, (3) recommended next step |
| Failure behavior | Explicit — out-of-scope requests get a polite explanation and a pointer to an appropriate human/university channel |
| Known limitations | Still no grounding in real university documents (by design — this is the Week 2 vs. Week 3 comparison point); relies on the model following instructions rather than a deterministic enforcement layer |

System prompt text: see `agent-backend/llm/prompts.py::_V2_SYSTEM_PROMPT` (reproduced
in full in the Week 2 task brief and mirrored there for auditability).

---

## Why V2 is a meaningful iteration over V1

1. **Scope is enumerated, not implied.** V1 says what the assistant helps
   with in general terms; V2 lists supported request types explicitly,
   which reduces ambiguity about what "general university questions"
   covers.
2. **Safety boundaries are itemized and expanded.** V1 has one sentence
   covering four high-impact decision categories. V2 splits these into
   individual constraints and adds boundaries V1 does not mention at
   all — notably, never claiming to have checked a system, created a
   ticket, or looked up a case status. This matters because a naive
   foundation-model baseline will readily role-play "I've submitted your
   request" even though no such backend action exists yet.
3. **Output is structured.** V1 allows free-form prose, which is harder
   to evaluate consistently. V2's three-part format (answer / limitation
   / next step) gives every response a predictable shape that later
   evaluation tooling (and, in Week 3+, a UI) can rely on.
4. **Failure behavior is explicit.** V1 relies on the model to
   improvise when a request is out of scope. V2 tells it exactly what to
   do: explain the limitation and redirect to a human/university
   channel.

## Known limitation carried by both versions

Neither prompt version grants the model access to real university
policies, deadlines, or procedures. This is intentional for Week 2: the
baseline must demonstrate that the model does *not* invent
university-specific facts it cannot know. Week 3 introduces retrieval
over approved documents so the same questions can be answered with
grounded sources, which is the intended Week 2 → Week 3 comparison.
