# Model Selection Note — Week 2 Baseline

## Decision

The Week 2 baseline uses Groq as the external foundation-model provider for the University Student-Support Case Agent.

## Rationale

Groq is an appropriate choice for this project because it gives the case agent a working, low-friction baseline without the operational burden of running and maintaining a local model. This is important in a short academic timeline with varied hardware across team members.

- Accessibility: an API key and a small SDK integration are enough to run the baseline on any developer machine.
- Integration simplicity: the `groq` Python SDK exposes an OpenAI-compatible chat-completions interface, so the case agent can keep a clean provider boundary and remain easy to switch later.
- Latency: Groq is designed for fast inference, which fits an interactive student-support workflow.
- Cost: Groq offers a usable development-tier option for prototyping without large upfront infrastructure costs.
- Privacy: the project currently uses only synthetic/example student questions, keeping third-party API exposure limited while the team validates the prompt and response flow.
- Operational safety: the backend explicitly handles configuration and provider failures, returning controlled errors instead of crashing or leaking internal details.

This keeps the team focused on the core Week 2 objective: validating a clean request → prompt → model → response path for the case agent, plus safe error handling and prompt design. The LLM boundary is already isolated behind `agent-backend/llm/service.py` and `agent-backend/llm/client.py`, which makes later upgrades such as RAG, retrieval, or provider replacement straightforward.

## Alternatives considered

- Local model hosting: rejected for now because of hardware variability, setup overhead, and the additional operational burden in an 8-week project.
- Other hosted providers (for example OpenAI): not rejected outright, but Groq was preferred for this baseline and the abstraction layer keeps the switch low-risk.

## Conclusion

For Week 2, Groq offers the best trade-off among speed, simplicity, cost, and delivery risk for the student-support case agent. The project remains provider-agnostic at the service boundary, so the model choice can be revisited later without redesigning the application flow.
