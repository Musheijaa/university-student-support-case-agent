const DECISION_LABELS = {
  tool_call: '🔧 Tool call',
  final_answer: '✅ Final answer',
  stop: '🛑 Stop',
  error: '❌ Error',
}

const STATUS_COLOURS = {
  completed: '#22c55e',
  human_approval_required: '#eab308',
  max_iterations_reached: '#ef4444',
  max_tool_calls_reached: '#ef4444',
  tool_not_approved: '#ef4444',
  llm_error: '#ef4444',
  running: '#3b82f6',
}

export default function AgentStepsCard({ agentResult }) {
  const { run_id, status, iteration_count, tool_call_count, steps } = agentResult
  const colour = STATUS_COLOURS[status] || '#999'

  return (
    <div className="agent-trace-card">
      <div className="agent-trace-header">
        <span className="agent-trace-title">Agent Execution Trace</span>
        <span className="agent-status-pill" style={{ borderColor: colour, color: colour }}>
          {status.replace(/_/g, ' ')}
        </span>
      </div>

      <div className="agent-trace-meta">
        <span>run: <code>{run_id.slice(0, 8)}…</code></span>
        <span>iterations: <strong>{iteration_count}</strong></span>
        <span>tool calls: <strong>{tool_call_count}</strong></span>
      </div>

      <div className="agent-steps">
        {steps.map((step, i) => (
          <div key={i} className={`agent-step agent-step-${step.decision}`}>
            <div className="agent-step-header">
              <span className="agent-step-iter">iter {step.iteration}</span>
              <span className="agent-step-decision">
                {DECISION_LABELS[step.decision] || step.decision}
              </span>
              {step.tool_name && (
                <code className="agent-step-tool">{step.tool_name}</code>
              )}
            </div>

            {step.tool_arguments && Object.keys(step.tool_arguments).length > 0 && (
              <div className="agent-step-row">
                <span className="agent-step-label">args</span>
                <code className="agent-step-value">
                  {JSON.stringify(step.tool_arguments)}
                </code>
              </div>
            )}

            {step.tool_result && (
              <div className="agent-step-row">
                <span className="agent-step-label">result</span>
                <span
                  className={`agent-step-value ${step.tool_result.success ? 'result-ok' : 'result-fail'}`}
                >
                  {step.tool_result.success
                    ? step.tool_result.sessions
                      ? `✓ ${step.tool_result.sessions.length} session(s) for ${step.tool_result.course_code}`
                      : step.tool_result.ticket_id
                        ? `✓ ${step.tool_result.ticket_id} — ${step.tool_result.status}`
                        : '✓ success'
                    : `✗ ${step.tool_result.error}`}
                </span>
              </div>
            )}

            {step.observation && (
              <div className="agent-step-row">
                <span className="agent-step-label">obs</span>
                <span className="agent-step-value agent-step-obs">{step.observation}</span>
              </div>
            )}

            {step.error && (
              <div className="agent-step-row">
                <span className="agent-step-label">error</span>
                <span className="agent-step-value result-fail">{step.error}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
