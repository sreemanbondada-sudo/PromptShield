import {
  afterEach,
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from 'vitest'

import {
  analyzePrompt,
  checkApiHealth,
  clearAccessToken,
  getAccessToken,
  getRecentEvents,
  isAuthenticated,
  loginAdmin,
  logoutAdmin,
  setAccessToken,
} from './api'


function createResponse({
  body,
  ok = true,
  status = 200,
}) {
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(body),
  }
}


describe('frontend API service', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    sessionStorage.clear()
    vi.unstubAllGlobals()
  })


  test('requests the public health endpoint', async () => {
    fetch.mockResolvedValue(
      createResponse({
        body: {
          status: 'healthy',
        },
      }),
    )

    const result = await checkApiHealth()

    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/health',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      }),
    )

    expect(
      fetch.mock.calls[0][1].headers.Authorization,
    ).toBeUndefined()

    expect(result).toEqual({
      status: 'healthy',
    })
  })


  test('logs in and stores the access token', async () => {
    fetch.mockResolvedValue(
      createResponse({
        body: {
          access_token: 'test-access-token',
          token_type: 'bearer',
          expires_in: 1800,
        },
      }),
    )

    const result = await loginAdmin(
      'admin',
      'correct-test-password',
    )

    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/auth/login',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          username: 'admin',
          password: 'correct-test-password',
        }),
      }),
    )

    expect(result.token_type).toBe('bearer')
    expect(getAccessToken()).toBe(
      'test-access-token',
    )
    expect(isAuthenticated()).toBe(true)
  })


  test('requires authentication for protected requests', async () => {
    await expect(
      getRecentEvents(5),
    ).rejects.toThrow(
      'Administrator authentication is required.',
    )

    expect(fetch).not.toHaveBeenCalled()
  })


  test('sends the bearer token with protected requests', async () => {
    setAccessToken('test-access-token')

    fetch.mockResolvedValue(
      createResponse({
        body: {
          events: [],
        },
      }),
    )

    await getRecentEvents(5)

    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/events?limit=5',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization:
            'Bearer test-access-token',
        }),
      }),
    )
  })


  test('sends prompts as authenticated JSON requests', async () => {
    setAccessToken('test-access-token')

    fetch.mockResolvedValue(
      createResponse({
        body: {
          recommended_action: 'allow',
        },
      }),
    )

    await analyzePrompt(
      'Explain the solar system.',
    )

    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/analyze',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          prompt: 'Explain the solar system.',
        }),
        headers: expect.objectContaining({
          Authorization:
            'Bearer test-access-token',
        }),
      }),
    )
  })


  test('uses the backend safe error message', async () => {
    setAccessToken('test-access-token')

    fetch.mockResolvedValue(
      createResponse({
        ok: false,
        status: 429,
        body: {
          error: 'rate_limit_exceeded',
          message:
            'Too many analysis requests. ' +
            'Please try again later.',
        },
      }),
    )

    await expect(
      analyzePrompt('Test prompt'),
    ).rejects.toThrow(
      'Too many analysis requests. ' +
        'Please try again later.',
    )
  })


  test('clears an expired unauthorized session', async () => {
    setAccessToken('expired-access-token')

    fetch.mockResolvedValue(
      createResponse({
        ok: false,
        status: 401,
        body: {
          detail: 'Invalid authentication credentials.',
        },
      }),
    )

    await expect(
      getRecentEvents(),
    ).rejects.toThrow(
      'Your administrator session has expired. ' +
        'Please sign in again.',
    )

    expect(getAccessToken()).toBeNull()
    expect(isAuthenticated()).toBe(false)
  })


  test('logs the administrator out', () => {
    setAccessToken('test-access-token')

    expect(isAuthenticated()).toBe(true)

    logoutAdmin()

    expect(getAccessToken()).toBeNull()
    expect(isAuthenticated()).toBe(false)
  })


  test('can clear a stored token directly', () => {
    setAccessToken('test-access-token')

    clearAccessToken()

    expect(getAccessToken()).toBeNull()
  })
})