import { useEffect, useRef, useState } from 'react'
import './App.css'
import { askStudentSupport, checkHealth } from './api'
import renderMarkdown from './markdown'
import TicketCard from './TicketCard'
import TimetableCard from './TimetableCard'

const STORAGE_KEY = 'unisupport-frontend-settings'

function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

let nextMessageId = 1

export default function App() {
  const saved = loadSettings()
  const [baseUrl, setBaseUrl] = useState(saved.baseUrl || 'http://127.0.0.1:8000')
  const [role, setRole] = useState(saved.role || 'student')
  const [userId, setUserId] = useState(saved.userId || 'demo-student')
  const [health, setHealth] = useState('unknown') // 'ok' | 'down' | 'unknown'

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const transcriptEndRef = useRef(null)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ baseUrl, role, userId }))
  }, [baseUrl, role, userId])

  useEffect(() => {
    let cancelled = false
    checkHealth(baseUrl)
      .then(() => !cancelled && setHealth('ok'))
      .catch(() => !cancelled && setHealth('down'))
    return () => {
      cancelled = true
    }
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
      const result = await askStudentSupport(baseUrl, question, role, userId)
      setMessages((prev) => [
        ...prev,
        {
          id: nextMessageId++,
          role: 'assistant',
          text: result.response,
          promptVersion: result.prompt_version,
          model: result.model,
          sources: result.sources || [],
          toolCalls: result.tool_calls || [],
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
        <h1>UniSupport AI — Test Console</h1>
        <div className="settings-row">
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
          <span className={`health-dot health-${health}`} title={`Backend: ${health}`} />
        </div>
      </header>

      <main className="transcript">
        {messages.length === 0 && (
          <p className="empty-hint">
            Ask a knowledge question (grounded in the policy corpus), a timetable question
            (e.g. "When is BSE4104 scheduled?"), or describe a problem (e.g. "I can't access
            the student portal") to see a support-ticket draft. Switch role to "staff" above
            to approve or reject a resulting ticket.
          </p>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} baseUrl={baseUrl} role={role} userId={userId} />
        ))}
        {loading && <div className="bubble assistant pending">Thinking…</div>}
        <div ref={transcriptEndRef} />
      </main>

      <form className="composer" onSubmit={handleSend}>
        <input
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

function MessageBubble({ message, baseUrl, role, userId }) {
  if (message.role === 'student') {
    return <div className="bubble student">{message.text}</div>
  }

  if (message.role === 'error') {
    return <div className="bubble error">{message.text}</div>
  }

  return (
    <div className="bubble assistant">
      <div className="response-text">{renderMarkdown(message.text)}</div>

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

      <div className="meta">
        {message.promptVersion} · {message.model}
      </div>
    </div>
  )
}
