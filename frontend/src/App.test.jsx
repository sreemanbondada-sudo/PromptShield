import {
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from 'vitest'

import App from './App'
import {
  analyzePrompt,
  checkApiHealth,
  getRecentEvents,
  getStatistics,
  verifyAuditChain,
} from './services/api'

vi.mock('./services/api', () => ({
  analyzePrompt: vi.fn(),
  checkApiHealth: vi.fn(),
  getRecentEvents: vi.fn(),
  getStatistics: vi.fn(),
  verifyAuditChain: vi.fn(),
}))

const SAFE_ANALYSIS = {
  event_id: 4,
  is_malicious: false,
  risk_level: 'low',
  risk_score: 10,
  category: 'safe',
  matched_patterns: [],
  explanation: 'No known malicious patterns were detected.',
  contains_sensitive_data: false,
  sensitive_findings: [],
  redacted_prompt: 'Explain the solar system.',
  recommended_action: 'allow',
  ml_prediction: false,
  ml_probability: 0.21,
  detection_sources: [],
}

describe('PromptShield dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    checkApiHealth.mockResolvedValue({
      status: 'healthy',
    })

    getStatistics.mockResolvedValue({
      total_scans: 3,
      malicious_prompts: 1,
      sensitive_prompts: 1,
      actions: {},
      categories: {},
    })

    verifyAuditChain.mockResolvedValue({
      valid: true,
      checked_events: 3,
      legacy_events: 0,
      broken_event_id: null,
    })

    getRecentEvents.mockResolvedValue({
      events: [],
    })

    analyzePrompt.mockResolvedValue(SAFE_ANALYSIS)
  })

  test('loads API status, statistics and audit integrity', async () => {
    render(<App />)

    expect(
      await screen.findByText('API online'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Total scans').closest('article'),
    ).toHaveTextContent('3')

    expect(
      screen
        .getByText('Malicious prompts')
        .closest('article'),
    ).toHaveTextContent('1')

    expect(
      screen
        .getByText('Sensitive prompts')
        .closest('article'),
    ).toHaveTextContent('1')

    expect(
      screen
        .getByText('Audit integrity')
        .closest('article'),
    ).toHaveTextContent('Verified')

    expect(
      screen
        .getByText('Audit integrity')
        .closest('article'),
    ).toHaveTextContent('3 events checked')
  })

  test('submits a prompt and displays its analysis', async () => {
    const user = userEvent.setup()

    render(<App />)

    await screen.findByText('API online')

    const promptInput = screen.getByLabelText(
      'Prompt to analyze',
    )

    await user.type(
      promptInput,
      'Explain the solar system.',
    )

    await user.click(
      screen.getByRole('button', {
        name: 'Analyze prompt',
      }),
    )

    await waitFor(() => {
      expect(analyzePrompt).toHaveBeenCalledWith(
        'Explain the solar system.',
      )
    })

    expect(
      await screen.findByText('Allow'),
    ).toBeInTheDocument()

    expect(screen.getByText('10/100')).toBeInTheDocument()
    expect(screen.getByText('Safe')).toBeInTheDocument()
    expect(screen.getByText('21%')).toBeInTheDocument()

    expect(
      screen.getByText('Security event #4'),
    ).toBeInTheDocument()
  })

  test('shows a safe error when analysis fails', async () => {
    const user = userEvent.setup()

    analyzePrompt.mockRejectedValueOnce(
      new Error(
        'Too many analysis requests. Please try again later.',
      ),
    )

    render(<App />)

    await screen.findByText('API online')

    await user.type(
      screen.getByLabelText('Prompt to analyze'),
      'Test prompt',
    )

    await user.click(
      screen.getByRole('button', {
        name: 'Analyze prompt',
      }),
    )

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent(
      'Too many analysis requests. Please try again later.',
    )
  })
})