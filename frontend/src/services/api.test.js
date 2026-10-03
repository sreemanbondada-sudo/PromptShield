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
  getRecentEvents,
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
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  test('requests the backend health endpoint', async () => {
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

    expect(result).toEqual({
      status: 'healthy',
    })
  })

  test('sends prompts as JSON for analysis', async () => {
    fetch.mockResolvedValue(
      createResponse({
        body: {
          recommended_action: 'allow',
        },
      }),
    )

    await analyzePrompt('Explain the solar system.')

    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/analyze',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          prompt: 'Explain the solar system.',
        }),
      }),
    )
  })

  test('requests a limited number of recent events', async () => {
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
      expect.any(Object),
    )
  })

  test('uses the backend safe error message', async () => {
    fetch.mockResolvedValue(
      createResponse({
        ok: false,
        status: 429,
        body: {
          error: 'rate_limit_exceeded',
          message:
            'Too many analysis requests. Please try again later.',
        },
      }),
    )

    await expect(
      analyzePrompt('Test prompt'),
    ).rejects.toThrow(
      'Too many analysis requests. Please try again later.',
    )
  })
})