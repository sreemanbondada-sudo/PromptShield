const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function request(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  const responseBody = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(
      responseBody?.message ??
        responseBody?.detail ??
        `Request failed with status ${response.status}`,
    )
  }

  return responseBody
}

export function checkApiHealth() {
  return request('/health')
}

export function analyzePrompt(prompt) {
  return request('/analyze', {
    method: 'POST',
    body: JSON.stringify({
      prompt,
    }),
  })
}

export function getStatistics() {
  return request('/statistics')
}

export function verifyAuditChain() {
  return request('/audit/verify')
}

export function getRecentEvents(limit = 10) {
  return request(`/events?limit=${limit}`)
}

