"""Stable, machine-readable error codes recorded in traces and logs.

Human-facing error messages can be reworded freely; these codes cannot,
because traces, log queries, and evidence files key off them. Every
failure the agent can observe maps to exactly one code here.
"""

# Model provider (llm/client.py)
LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"
LLM_TIMEOUT = "LLM_TIMEOUT"
LLM_CONNECTION_ERROR = "LLM_CONNECTION_ERROR"
LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
LLM_HTTP_ERROR = "LLM_HTTP_ERROR"  # suffixed with the status code, e.g. LLM_HTTP_401
LLM_API_ERROR = "LLM_API_ERROR"
LLM_EMPTY_RESPONSE = "LLM_EMPTY_RESPONSE"

# Retrieval (rag/)
RETRIEVAL_ERROR = "RETRIEVAL_ERROR"

# Tool dispatch (tools/registry.py)
TOOL_UNKNOWN = "TOOL_UNKNOWN"
TOOL_INVALID_JSON = "TOOL_INVALID_JSON"
TOOL_UNAUTHORIZED = "TOOL_UNAUTHORIZED"
TOOL_INVALID_INPUT = "TOOL_INVALID_INPUT"
TOOL_DATA_UNAVAILABLE = "TOOL_DATA_UNAVAILABLE"
TOOL_STORE_UNAVAILABLE = "TOOL_STORE_UNAVAILABLE"
TOOL_UNEXPECTED_ERROR = "TOOL_UNEXPECTED_ERROR"
TOOL_OUTPUT_INVALID = "TOOL_OUTPUT_INVALID"
TOOL_NO_RESULT = "TOOL_NO_RESULT"  # tool ran but reported success=false (e.g. unknown course)

# Agent contract (agent/orchestrator.py)
AGENT_TOOL_NOT_APPROVED = "AGENT_TOOL_NOT_APPROVED"
AGENT_TOOL_BUDGET_EXHAUSTED = "AGENT_TOOL_BUDGET_EXHAUSTED"
AGENT_ITERATION_BUDGET_EXHAUSTED = "AGENT_ITERATION_BUDGET_EXHAUSTED"
AGENT_UNHANDLED_EXCEPTION = "AGENT_UNHANDLED_EXCEPTION"


def llm_http_error(status_code: int) -> str:
    return f"{LLM_HTTP_ERROR}_{status_code}"
