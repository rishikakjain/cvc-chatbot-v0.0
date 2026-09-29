import { mockSendMessage } from './mockApi'

const API_URL = import.meta.env.VITE_API_URL
const USE_MOCK = !API_URL

let sessionId = sessionStorage.getItem('cvc_session_id') || null

export async function sendMessage(message, filters = {}) {
  if (USE_MOCK) {
    return mockSendMessage(message)
  }

  const headers = {
    'Content-Type': 'application/json',
    ...(sessionId ? { 'X-Session-Id': sessionId } : {}),
  }

  const resp = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, ...filters }),
  })

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.error || `HTTP ${resp.status}`)
  }

  const data = await resp.json()

  if (data.session_id && data.session_id !== sessionId) {
    sessionId = data.session_id
    sessionStorage.setItem('cvc_session_id', sessionId)
  }

  return data
}

export function clearSession() {
  sessionId = null
  sessionStorage.removeItem('cvc_session_id')
}

export function isMockMode() {
  return USE_MOCK
}
