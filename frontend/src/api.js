// Thin fetch wrapper around the agent-backend API.
// See docs/tool-catalogue.md for what X-User-Role/X-User-Id mean -
// this is a bounded role simulation, not real authentication.

async function request(baseUrl, path, options = {}, role, userId) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Role': role,
      'X-User-Id': userId || 'anonymous',
      ...(options.headers || {}),
    },
  })

  let body = null
  try {
    body = await response.json()
  } catch {
    // no JSON body (e.g. a network-level failure) - body stays null
  }

  if (!response.ok) {
    const detail = body?.detail || body?.error || `Request failed (HTTP ${response.status})`
    throw new Error(detail)
  }
  return body
}

export function checkHealth(baseUrl) {
  return request(baseUrl, '/health', { method: 'GET' }, 'student', 'health-check')
}

export function askStudentSupport(baseUrl, message, role, userId) {
  return request(
    baseUrl,
    '/api/v1/student-support',
    { method: 'POST', body: JSON.stringify({ message }) },
    role,
    userId,
  )
}

export function approveTicket(baseUrl, ticketId, role, userId) {
  return request(
    baseUrl,
    `/api/v1/support-tickets/${encodeURIComponent(ticketId)}/approve`,
    { method: 'POST' },
    role,
    userId,
  )
}

export function rejectTicket(baseUrl, ticketId, role, userId) {
  return request(
    baseUrl,
    `/api/v1/support-tickets/${encodeURIComponent(ticketId)}/reject`,
    { method: 'POST' },
    role,
    userId,
  )
}
