const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

const ACCESS_TOKEN_STORAGE_KEY =
  'promptshield_access_token'


export function getAccessToken() {
  return sessionStorage.getItem(
    ACCESS_TOKEN_STORAGE_KEY,
  )
}


export function setAccessToken(accessToken) {
  sessionStorage.setItem(
    ACCESS_TOKEN_STORAGE_KEY,
    accessToken,
  )
}


export function clearAccessToken() {
  sessionStorage.removeItem(
    ACCESS_TOKEN_STORAGE_KEY,
  )
}


export function isAuthenticated() {
  return Boolean(getAccessToken())
}


async function request(
  endpoint,
  {
    authenticated = true,
    ...options
  } = {},
) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (authenticated) {
    const accessToken = getAccessToken()

    if (!accessToken) {
      throw new Error(
        'Administrator authentication is required.',
      )
    }

    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      ...options,
      headers,
    },
  )

  const responseBody = await response
    .json()
    .catch(() => null)

  if (!response.ok) {
    if (
      authenticated &&
      response.status === 401
    ) {
      clearAccessToken()

      throw new Error(
        'Your administrator session has expired. ' +
          'Please sign in again.',
      )
    }

    throw new Error(
      responseBody?.message ??
        responseBody?.detail ??
        `Request failed with status ${response.status}`,
    )
  }

  return responseBody
}


export function checkApiHealth() {
  return request('/health', {
    authenticated: false,
  })
}


export async function loginAdmin(
  username,
  password,
) {
  const result = await request('/auth/login', {
    method: 'POST',
    authenticated: false,
    body: JSON.stringify({
      username,
      password,
    }),
  })

  setAccessToken(result.access_token)

  return result
}


export function logoutAdmin() {
  clearAccessToken()
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

