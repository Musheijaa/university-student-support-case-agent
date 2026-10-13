# Workflow Traces

This folder is reserved for workflow traces and evidence logs.

Examples may include:
- request-to-response trace logs
- case-state transition logs
- routing decision traces
- human review and escalation evidence

These should be captured as the implementation progresses. The folder is intentionally empty at the Week 1 planning stage.

## Contents

- [`week5/`](week5/README.md) — bounded agent execution traces, one per contract stop path.
- [`observability/`](observability/README.md) — end-to-end observability traces (normal, boundary
  and error runs) with model parameters, prompt version, RAG relevance scores, tool I/O, latency,
  error codes and terminal status. Schema: [`docs/observability.md`](../../docs/observability.md).
