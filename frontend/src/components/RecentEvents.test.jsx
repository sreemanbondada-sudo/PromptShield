import {
  render,
  screen,
} from '@testing-library/react'
import {
  describe,
  expect,
  test,
} from 'vitest'

import RecentEvents from './RecentEvents'

const SAMPLE_EVENTS = [
  {
    id: 2,
    created_at: '2026-10-03 06:30:00',
    recommended_action: 'block',
    risk_score: 100,
    risk_level: 'high',
    category: 'prompt_injection',
    contains_sensitive_data: false,
  },
  {
    id: 1,
    created_at: '2026-10-03 06:25:00',
    recommended_action: 'redact',
    risk_score: 60,
    risk_level: 'medium',
    category: 'sensitive_data_exposure',
    contains_sensitive_data: true,
  },
]

describe('RecentEvents', () => {
  test('shows an empty message when there are no events', () => {
    render(<RecentEvents events={[]} />)

    expect(
      screen.getByText(
        'No security events have been recorded yet.',
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Showing 0 recent events'),
    ).toBeInTheDocument()
  })

  test('renders recent event information', () => {
    render(<RecentEvents events={SAMPLE_EVENTS} />)

    expect(
      screen.getByText('Showing 2 recent events'),
    ).toBeInTheDocument()

    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(screen.getByText('#1')).toBeInTheDocument()

    expect(screen.getByText('Block')).toBeInTheDocument()
    expect(screen.getByText('Redact')).toBeInTheDocument()

    expect(
      screen.getByText('Prompt Injection'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Sensitive Data Exposure'),
    ).toBeInTheDocument()
  })

  test('shows whether sensitive data was detected', () => {
    render(<RecentEvents events={SAMPLE_EVENTS} />)

    expect(
      screen.getByText('Detected'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('None'),
    ).toBeInTheDocument()
  })
})