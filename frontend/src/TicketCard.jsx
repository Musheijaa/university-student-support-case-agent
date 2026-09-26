import { useState } from 'react'
import { approveTicket, rejectTicket } from './api'

const STATUS_LABELS = {
  PENDING_APPROVAL: 'Pending approval',
  SUBMITTED: 'Submitted',
  REJECTED: 'Rejected',
}

export default function TicketCard({ baseUrl, role, userId, invocationResult }) {
  const [status, setStatus] = useState(invocationResult.status)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (!invocationResult.success) {
    return (
      <div className="tool-card tool-card-error">
        Could not create a support ticket: {invocationResult.error}
      </div>
    )
  }

  const canModerate = role === 'staff' && status === 'PENDING_APPROVAL'

  async function handleDecision(action) {
    setBusy(true)
    setError(null)
    try {
      const fn = action === 'approve' ? approveTicket : rejectTicket
      const result = await fn(baseUrl, invocationResult.ticket_id, role, userId)
      if (result.success) {
        setStatus(result.status)
      } else {
        setError(result.error)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="tool-card">
      <div className="tool-card-title">Support Ticket Draft</div>
      <dl className="ticket-fields">
        <dt>Ticket ID</dt>
        <dd>{invocationResult.ticket_id}</dd>
        <dt>Category</dt>
        <dd>{invocationResult.category}</dd>
        <dt>Subject</dt>
        <dd>{invocationResult.subject}</dd>
        <dt>Status</dt>
        <dd>
          <span className={`status-pill status-${status?.toLowerCase()}`}>
            {STATUS_LABELS[status] || status}
          </span>
        </dd>
      </dl>

      {canModerate && (
        <div className="ticket-actions">
          <button disabled={busy} onClick={() => handleDecision('approve')}>
            Approve
          </button>
          <button disabled={busy} className="secondary" onClick={() => handleDecision('reject')}>
            Reject
          </button>
        </div>
      )}
      {!canModerate && status === 'PENDING_APPROVAL' && (
        <p className="hint">Switch to the staff role above to approve or reject this ticket.</p>
      )}
      {error && <p className="error-text">{error}</p>}
    </div>
  )
}
