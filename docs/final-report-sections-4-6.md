# Final Report: Sections 4-6

This document contains sections 4, 5, and 6 of the final engineering
report. Sections 1-3 (problem, requirements, architecture) and sections
7-10 (memory, evaluation, software engineering, reflection) are written
separately by other team members.

Every claim below refers to actual code in the repository. Where the
fuller design is documented elsewhere, that file is cited so the reader
can go deeper.


## 4. Foundation Model and Prompt Engineering

### 4.1 Model rationale

The system uses a single external foundation model, `openai/gpt-oss-20b`,
served through the Groq API. This choice was deliberate: it delivers
strong reasoning at low latency, requires no local GPU, and lets the
project focus on the parts of AI engineering the brief rewards -
prompting, retrieval, tools, and guardrails - rather than on
infrastructure that would consume the eight-week window. The full
rationale is documented in `docs/model-selection.md`. There is no
model-level training or fine-tuning; the model is used as a service
behind a versioned interface.

### 4.2 Prompt architecture

Prompts are stored as first-class artifacts in
`agent-backend/llm/prompts.py` and versioned. Five versions exist:

- `V1.0` - initial baseline: role definition and a basic instruction
  not to invent answers.
- `V2.0` - explicit scope, response shape, and refusal behaviour.
- `rag-v1.0` - adds the retrieved evidence block and citation
  requirements introduced in Week 3.
- `tools-v1.0` - adds the two tool schemas and the instruction to draft
  (not submit) a ticket, introduced in Week 4.
- `agent-v1.0` - adds bounded-agent rules: one decision per iteration,
  re-plan after each tool result, never retry a failed tool blindly,
  draft at most one ticket, and state plainly that only staff can
  approve. This is the version served by
  `POST /api/v1/agent/student-support`.

Every version is retained in the file. The active version is selected
by `active_prompt_version` in `agent-backend/config.py`, which means
the choice is versioned, reversible, and auditable. The complete
content of each template and the design intent behind each is
documented in `docs/prompt-specification.md`.

### 4.3 Iteration and evaluation

Prompt iterations were driven by evidence, not taste. Baseline
evaluation is documented in `docs/prompt-evaluation.md`: each prompt
version was exercised against a fixed set of questions and compared for
groundedness, refusal behaviour, and instruction-following before
being adopted. V2.0 fixed observed failures in V1.0 (over-broad claims,
missing refusal on high-impact topics). The `rag-v1.0` prompt was
introduced alongside retrieval because a bare-model prompt cannot cite
sources it was never given. The `tools-v1.0` prompt was introduced
alongside tool calling for the same reason. Each change is tied to a
specific failure or capability gap rather than a generic "improvement".

### 4.4 Where prompt engineering stops

Prompt instructions are important but never the last line of defence.
Every safety boundary in the system - the tool allow-list, role
authorization, loop budgets, human-approval gates - is enforced in
Python, not in prose. This decision is stated explicitly because it is
the design principle that makes the system auditable: the model can be
wrong, adversarial, or malicious, and the code will still refuse to
exceed the agent's bounds. Details of the code-level enforcement are in
sections 6 and 8.


## 5. Context Engineering and RAG

### 5.1 The problem RAG solves here

The foundation model has no reliable knowledge of Makerere University's
specific policies. Asking it directly would produce plausible-sounding
answers that cite nothing. Retrieval-augmented generation fixes this by
supplying a small set of curated passages from approved institutional
documents as context, and by requiring the model to answer from those
passages rather than from memory. The result is grounded, cite-able,
and auditable.

### 5.2 The corpus

The corpus is the set of documents under
`docs/makerereUniversityPolicyDocs/`, registered in
`docs/corpus-source-register.md`. Every document has an ID (`DOC001`,
`DOC002`, ...), a title, a source, and a stated reason for being
approved. The corpus is intentionally small and curated - not "all of
the internet" and not "all of Makerere's drives". Two design rules
apply: only public/approved documents are used, and any document can
be traced from a citation back to its registered source.

### 5.3 Pipeline

The pipeline is documented in `docs/rag-architecture.md` and
implemented across `agent-backend/rag/`:

1. `rag/loader.py` reads each PDF from the corpus directory and
   extracts text page by page.
2. `rag/chunker.py` splits long pages into chunks with overlap so that
   no sentence is cut mid-thought. Each chunk retains its document ID
   and page number.
3. `rag/embeddings.py` computes embeddings with a local ONNX MiniLM
   model (`chroma-default`), so no external embedding API is required.
4. `rag/vector_store.py` stores the chunks in a persistent ChromaDB
   collection under `agent-backend/data/chroma/`. Ingest is idempotent:
   running `ingest.py` again does not duplicate chunks.
5. At query time, `rag/retriever.py` embeds the student's question with
   the same model, finds the closest chunks, filters by
   `RAG_MIN_SCORE` (default 0.35), and returns the top `RAG_TOP_K`
   (default 4) chunks plus their metadata.
6. `rag/context_builder.py` turns those chunks into two outputs: an
   evidence block to include in the prompt, and a source list to
   return to the caller. The source list is deduplicated by
   (document, page) and never fabricates a page number.

### 5.4 Grounding and the failure path

The system is grounded by construction: the model is asked to answer
from the evidence block and to cite the sources it used. The API
response contains both a `sources` array (for the user) and the
`prompt_version` that produced the answer (for audit).

Grounding has an explicit failure path. If the retriever returns no
chunks above the score threshold, the context builder emits a
"no relevant evidence" message and the model is instructed to say so
plainly rather than invent an answer. This is covered by
`tests/test_context_builder.py::test_empty_chunks_produce_no_evidence_message`
and `tests/test_retriever.py::test_retrieve_empty_matches_means_no_evidence`.
The four known retrieval failures discovered during Week 3 are
documented in `docs/rag-failures.md`; they remain open limitations and
are also visible in `tests/test_retriever.py`.

### 5.5 Evaluation

Retrieval quality is documented in `docs/rag-evaluation.md`. The
evaluation set includes questions the corpus can answer (with expected
source pages) and questions it cannot, and the metrics tracked are
retrieval precision (did the right pages come back?) and answer
groundedness (did the model use only those pages?). Known weak points -
for example, questions phrased in ways that do not match the corpus
vocabulary - are documented rather than hidden.


## 6. Tools and Agentic Workflow

### 6.1 The tool layer

Two tools are exposed to the model, registered in exactly one place,
`agent-backend/tools/registry.py` (`TOOL_REGISTRY`). Nothing outside
that allow-list is callable. The two tools are:

- `check_timetable` - read-only lookup against
  `data/timetable/timetable.json`. Returns scheduled sessions for a
  course code, optionally filtered to a date.
- `create_support_ticket` - writes a `PENDING_APPROVAL` draft to
  `data/tickets.db`. Never submits or approves anything.

Every tool call is dispatched through
`tools/registry.py::dispatch_tool_call`, which enforces, in this exact
order: (1) the tool is on the allow-list; (2) arguments parse as JSON;
(3) the caller's role is authorized for that tool; (4) arguments
validate against the tool's Pydantic input schema; (5) the tool
executes; (6) the result validates against the output schema. A
failure at any step returns `{"success": false, "error": ...}` to the
agent as an observation. The tool executor never raises; it always
returns a dict. The full schemas, role matrix, and failure behaviour
are documented in `docs/tool-catalogue.md`.

### 6.2 Human-in-the-loop for the higher-impact action

The two actions differ in risk. Reading the timetable changes nothing.
Drafting a ticket creates real state, but it is a draft - it cannot
notify staff or trigger a workflow until a human moves it. This
distinction is enforced architecturally: `approve_ticket` and
`reject_ticket` are *not registered as tools*. They exist only as
staff-only HTTP endpoints (`POST /api/v1/support-tickets/{id}/approve`
and `/reject`) that require `X-User-Role: staff` and return 403 to
anyone else. There is no code path by which the model can submit or
approve a ticket.

This is a structural guarantee, not a prompt instruction. Even a fully
adversarial model that "decides" to approve a ticket cannot succeed -
the tool it would have to call does not exist.

### 6.3 The bounded agent loop

Week 5 added a bounded agent loop (`agent-backend/agent/orchestrator.py`)
that runs on top of the tool layer. Each iteration:

1. Asks the model for the next decision (final answer or a tool call).
2. If the model requests a tool: validates against the contract,
   dispatches it through the tool registry, records the observation,
   and re-plans.
3. If the model returns a final answer: stops with an appropriate
   terminal status.

The loop is bounded in two independent ways: `max_iterations`
(`agent_max_iterations`, default 4) and `max_tool_calls` (default 3).
Both are enforced by the loop guard, not by asking the model to
behave. A misbehaving provider that ignores `tool_choice="none"` still
cannot cause more than `max_tool_calls` tool executions - this is
verified by
`tests/test_tool_calling_flow.py::test_tool_execution_is_hard_capped_even_if_provider_ignores_tool_choice`.

Every run ends in exactly one terminal status: `completed`,
`human_approval_required`, `max_iterations_reached`,
`max_tool_calls_reached`, `tool_not_approved`, or `llm_error`. There
is no code path that leaves a run `running`.

### 6.4 Agent Task Contract

The agent's goal, approved tools, iteration limit, tool limit, and
terminal statuses are declared in a single artifact - the Agent Task
Contract - that is both a document (`docs/agent-task-contract.md`) and
a Python class (`agent/contract.py::AgentTaskContract`). The class is
built from the same settings the loop reads, so the document and the
enforcement cannot drift apart. Adding a tool to the allow-list is not
possible without also adding it to the registry, because the
`approved_tools` set is derived from `TOOL_REGISTRY` itself.

### 6.5 Progression from model to agent

The system progressed deliberately week by week:

- Week 2: foundation model behind a versioned prompt.
- Week 3: RAG grounding and source citations.
- Week 4: two explicit tools with strict dispatch.
- Week 5: bounded agent loop on top of the tools.
- Week 6: bounded per-session memory (see section 7).
- Week 7: adversarial testing and guardrail evidence (see section 8).

Each layer builds on the previous one; none replaces it. The final
system still answers a RAG-grounded question in one shot when the
question needs no tool, still dispatches through the same registry
choke point when a tool is needed, and still refuses anything outside
the contract's goal. The progression is the point: the system does not
claim more autonomy than it has been carefully engineered to use.
