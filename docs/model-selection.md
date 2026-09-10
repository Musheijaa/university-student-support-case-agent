# Model Selection Note — Week 2 Baseline

## Decision

The Week 2 baseline uses an external foundation-model API (Groq) rather
than a locally hosted model.

## Rationale

**Accessibility.** An API key and an HTTP call are enough to get a
working baseline running on any team member's machine, without
requiring a GPU or a multi-gigabyte model download. This matters for a
5-person student team on a tight 8-week schedule with heterogeneous
hardware.

**Integration simplicity.** The `groq` Python SDK exposes an
OpenAI-compatible chat-completions interface, which keeps the
integration code in `agent-backend/llm/client.py` small and easy to reason about,
and easy to swap for another OpenAI-compatible provider later if needed.

**Latency.** Groq's infrastructure is built around custom inference
hardware (LPUs) specifically optimized for low-latency token
generation, which is a reasonable fit for an interactive support
assistant. Exact latency figures are provider- and load-dependent and
are not claimed here; they should be measured against our own traffic
if latency becomes a concern.

**Cost considerations.** Groq offers a usable free/low-cost tier for
development-scale traffic, which fits an academic prototype's budget.
We do not restate specific pricing figures here since they change over
time — see Groq's own pricing page for current numbers before making
budget commitments.

**Privacy considerations.** No confidential university or student data
is used in this project (per the project's Responsible AI note in the
root `README.md`). Only synthetic/example student questions are sent to
the external API in Week 2. This keeps the privacy exposure of using a
third-party API limited. If real student data is ever considered in a
later phase, this decision would need to be revisited alongside a data
processing/privacy review.

**API dependency.** Using an external provider introduces a hard
dependency on Groq's availability and rate limits. The baseline handles
this explicitly (see `agent-backend/llm/client.py` and the error-handling section
of `agent-backend/main.py`): configuration errors return `503`, provider/network
errors return `502`, and no request ever crashes the process or leaks
internal details.

**Suitability for the Week 2 baseline.** Week 2's only goal is to prove
a clean request → prompt → model → response path exists and is safe.
An external API lets us focus entirely on that path — prompt design,
validation, and error handling — instead of on model hosting and
inference infrastructure.

**Future extensibility.** The LLM interaction is isolated behind
`agent-backend/llm/service.py` and `agent-backend/llm/client.py`. Week 3's RAG layer can
inject retrieved context into the prompt ahead of the existing client
call, and later LangGraph-based orchestration can call the same service
as one node in a larger graph, without requiring changes to the FastAPI
route itself.

## Alternatives considered (not selected for Week 2)

- **Locally hosted open-weight model:** rejected for now due to
  hardware variability across team members' machines and the added
  operational complexity of managing model weights and inference
  servers within an 8-week academic timeline. May be revisited later
  purely as a cost/privacy trade-off discussion, not a Week 2 blocker.
- **Other hosted providers (e.g. OpenAI):** not rejected outright, but
  Groq was preferred per the project brief; the client abstraction in
  `agent-backend/llm/client.py` keeps switching providers a contained change.
