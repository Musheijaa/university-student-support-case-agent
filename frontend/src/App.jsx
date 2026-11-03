import { useEffect, useRef, useState } from 'react'
import './App.css'
import { askAgentSupport, checkHealth } from './api'
import AgentStepsCard from './AgentStepsCard'
import renderMarkdown from './markdown'
import TicketCard from './TicketCard'
import TimetableCard from './TimetableCard'

const STORAGE_KEY = 'unisupport-frontend-settings'
const CHAT_STORAGE_KEY = 'unisupport-frontend-chat'

function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

function loadMessages() {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

let nextMessageId = 1

export default function App() {
  const saved = loadSettings()
  const [baseUrl, setBaseUrl] = useState(saved.baseUrl || 'http://127.0.0.1:8000')
  const [role, setRole] = useState(saved.role || 'student')
  const [userId, setUserId] = useState(saved.userId || 'demo-student')
  const [showTrace, setShowTrace] = useState(saved.showTrace ?? false)
  const [health, setHealth] = useState('unknown')

  const [messages, setMessages] = useState(() => {
    const restored = loadMessages()
    const maxId = restored.reduce((max, m) => Math.max(max, m.id || 0), 0)
    nextMessageId = maxId + 1
    return restored
  })
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const transcriptEndRef = useRef(null)
  const inputRef = useRef(null)

  function fillInput(text) {
    setInput(text)
    inputRef.current?.focus()
  }

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ baseUrl, role, userId, showTrace }))
  }, [baseUrl, role, userId, showTrace])

  useEffect(() => {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages))
  }, [messages])

  function handleClearChat() {
    setMessages([])
  }

  useEffect(() => {
    let cancelled = false
    checkHealth(baseUrl)
      .then(() => !cancelled && setHealth('ok'))
      .catch(() => !cancelled && setHealth('down'))
    return () => { cancelled = true }
  }, [baseUrl])

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(event) {
    event.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    const userMessage = { id: nextMessageId++, role: 'student', text: question }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const result = await askAgentSupport(baseUrl, question, role, userId)
      // Extract tool calls from the agent's step trace for the
      // TimetableCard/TicketCard renderers (shown either way - they're
      // part of the answer, not just trace detail).
      const toolCalls = (result.steps || [])
        .filter((s) => s.decision === 'tool_call' && s.tool_result)
        .map((s) => ({ tool: s.tool_name, result: s.tool_result }))
      setMessages((prev) => [
        ...prev,
        {
          id: nextMessageId++,
          role: 'assistant',
          text: result.response,
          agentResult: result,
          toolCalls,
          sources: result.sources || [],
          promptVersion: result.prompt_version,
          model: result.model,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: nextMessageId++, role: 'error', text: err.message },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-title-row">
          <h1>UniSupport AI — Test Console</h1>
          <div className="topbar-title-actions">
            {messages.length > 0 && (
              <button type="button" className="link-button" onClick={handleClearChat}>
                Clear chat
              </button>
            )}
            <span className={`health-dot health-${health}`} title={`Backend: ${health}`} />
          </div>
        </div>
        <div className="settings-panel">
          <label>
            Backend URL
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://127.0.0.1:8000"
            />
          </label>
          <label>
            Role
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="student">student</option>
              <option value="staff">staff</option>
              <option value="guest">guest</option>
            </select>
          </label>
          <label>
            User ID
            <input value={userId} onChange={(e) => setUserId(e.target.value)} />
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={showTrace}
              onChange={(e) => setShowTrace(e.target.checked)}
            />
            Show execution trace
          </label>
        </div>
      </header>

      <main className="transcript">
        {messages.length === 0 && (
          <div className="empty-state">
            <p className="empty-state-title">Ask a question to get started</p>
            <div className="suggestion-chips">
              <button type="button" onClick={() => fillInput('What counts as examination malpractice at Makerere?')}>
                Policy question
              </button>
              <button type="button" onClick={() => fillInput('When is BSE4104 scheduled?')}>
                Timetable lookup
              </button>
              <button type="button" onClick={() => fillInput("I can't access the student portal")}>
                Report a problem
              </button>
            </div>
            <p className="empty-state-hint">
              Switch role to "staff" to approve or reject a resulting support ticket. Tick "Show
              execution trace" to see the agent's plan/act/observe steps behind each answer.
            </p>
          </div>
        )}
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            baseUrl={baseUrl}
            role={role}
            userId={userId}
            showTrace={showTrace}
          />
        ))}
        {loading && <div className="bubble assistant pending">Thinking…</div>}
        <div ref={transcriptEndRef} />
      </main>

      <form className="composer" onSubmit={handleSend}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question…"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}

function MessageBubble({ message, baseUrl, role, userId, showTrace }) {
  if (message.role === 'student') {
    return <div className="bubble student">{message.text}</div>
  }

  if (message.role === 'error') {
    return <div className="bubble error">{message.text}</div>
  }

  // The timetable/ticket tool cards below already show this data structured -
  // suppress the model's own markdown table so it isn't shown twice.
  const hasStructuredToolCard = message.toolCalls?.some(
    (c) => c.tool === 'check_timetable' || c.tool === 'create_support_ticket',
  )

  return (
    <div className="bubble assistant">
      {message.text && (
        <div className="response-text">
          {renderMarkdown(message.text, { suppressTables: hasStructuredToolCard })}
        </div>
      )}

      {message.toolCalls?.length > 0 && (
        <div className="tool-calls">
          {message.toolCalls.map((call, i) =>
            call.tool === 'check_timetable' ? (
              <TimetableCard key={i} invocationResult={call.result} />
            ) : call.tool === 'create_support_ticket' ? (
              <TicketCard
                key={i}
                baseUrl={baseUrl}
                role={role}
                userId={userId}
                invocationResult={call.result}
              />
            ) : (
              <div key={i} className="tool-card">
                {call.tool}: {JSON.stringify(call.result)}
              </div>
            ),
          )}
        </div>
      )}

      {showTrace && message.agentResult ? (
        <AgentStepsCard agentResult={message.agentResult} />
      ) : (
        <>
          {message.promptVersion && (
            <div className="meta">
              {message.promptVersion} · {message.model}
            </div>
          )}
          {message.sources?.length > 0 && (
            <div className="sources">
              <div className="sources-title">Sources</div>
              <ul>
                {message.sources.map((s, i) => (
                  <li key={i}>
                    {s.document} (p.{s.page})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}
