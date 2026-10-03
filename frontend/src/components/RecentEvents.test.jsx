import {
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  describe,
  expect,
  test,
  vi,
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
    is_malicious: true,
    contains_sensitive_data: false,
    sensitive_data_types: [],
    matched_patterns: [
      'previous-instruction override',
      'system-prompt extraction',
    ],
    prompt_length: 70,
    previous_hash: 'previous-test-hash',
    event_hash: 'current-test-hash',
  },
  {
    id: 1,
    created_at: '2026-10-03 06:25:00',
    recommended_action: 'redact',
    risk_score: 60,
    risk_level: 'medium',
    category: 'sensitive_data_exposure',
    is_malicious: false,
    contains_sensitive_data: true,
    sensitive_data_types: [
      'email_address',
    ],
    matched_patterns: [],
    prompt_length: 42,
    previous_hash: 'another-previous-hash',
    event_hash: 'another-current-hash',
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
      screen.getByText('Showing 0 of 0 events'),
    ).toBeInTheDocument()
  })

  test('renders recent event information', () => {
    render(<RecentEvents events={SAMPLE_EVENTS} />)

    expect(
      screen.getByText('Showing 2 of 2 events'),
    ).toBeInTheDocument()

    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(screen.getByText('#1')).toBeInTheDocument()

    expect(
      screen.getByText('Block', {
        selector: '.event-action',
      }),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Redact', {
        selector: '.event-action',
      }),
    ).toBeInTheDocument()

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

  test('filters events using the search field', async () => {
    const user = userEvent.setup()

    render(<RecentEvents events={SAMPLE_EVENTS} />)

    await user.type(
      screen.getByRole('searchbox', {
        name: 'Search events',
      }),
      'sensitive data',
    )

    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(
      screen.queryByText('#2'),
    ).not.toBeInTheDocument()

    expect(
      screen.getByText('Showing 1 of 2 events'),
    ).toBeInTheDocument()
  })

  test('filters events by recommended action', async () => {
    const user = userEvent.setup()

    render(<RecentEvents events={SAMPLE_EVENTS} />)

    await user.selectOptions(
      screen.getByRole('combobox', {
        name: 'Filter by action',
      }),
      'block',
    )

    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(
      screen.queryByText('#1'),
    ).not.toBeInTheDocument()

    expect(
      screen.getByText('Showing 1 of 2 events'),
    ).toBeInTheDocument()
  })

  test('clears filters when no events match', async () => {
    const user = userEvent.setup()

    render(<RecentEvents events={SAMPLE_EVENTS} />)

    const searchField = screen.getByRole('searchbox', {
      name: 'Search events',
    })

    await user.type(
      searchField,
      'does-not-exist',
    )

    expect(
      screen.getByText(
        'No events match the selected filters.',
      ),
    ).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', {
        name: 'Clear filters',
      }),
    )

    expect(searchField).toHaveValue('')
    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(screen.getByText('#1')).toBeInTheDocument()
  })

  test('refreshes recent events', async () => {
    const user = userEvent.setup()

    const onRefresh = vi
      .fn()
      .mockResolvedValue(undefined)

    render(
      <RecentEvents
        events={SAMPLE_EVENTS}
        onRefresh={onRefresh}
      />,
    )

    await user.click(
      screen.getByRole('button', {
        name: 'Refresh events',
      }),
    )

    expect(onRefresh).toHaveBeenCalledOnce()
  })

  test('shows a safe error when refresh fails', async () => {
    const user = userEvent.setup()

    const onRefresh = vi
      .fn()
      .mockRejectedValue(
        new Error('Private backend information'),
      )

    render(
      <RecentEvents
        events={SAMPLE_EVENTS}
        onRefresh={onRefresh}
      />,
    )

    await user.click(
      screen.getByRole('button', {
        name: 'Refresh events',
      }),
    )

    await waitFor(() => {
      expect(
        screen.getByRole('alert'),
      ).toHaveTextContent(
        'Recent events could not be refreshed.',
      )
    })

    expect(
      screen.queryByText(
        'Private backend information',
      ),
    ).not.toBeInTheDocument()
  })

  test('opens an event investigation view', async () => {
    const user = userEvent.setup()

    render(<RecentEvents events={SAMPLE_EVENTS} />)

    await user.click(
      screen.getByRole('button', {
        name: 'View details for event #2',
      }),
    )

    expect(
      screen.getByRole('dialog', {
        name: 'Security event #2',
      }),
    ).toBeInTheDocument()

    expect(
      screen.getByText(
        'Previous-Instruction Override',
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText(
        'System-Prompt Extraction',
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText('70 characters'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('previous-test-hash'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('current-test-hash'),
    ).toBeInTheDocument()

    expect(
      screen.getByText(
        /Original prompt contents are not exposed/,
      ),
    ).toBeInTheDocument()
  })

  test('closes the event investigation view', async () => {
    const user = userEvent.setup()

    render(<RecentEvents events={SAMPLE_EVENTS} />)

    await user.click(
      screen.getByRole('button', {
        name: 'View details for event #2',
      }),
    )

    expect(
      screen.getByRole('dialog'),
    ).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', {
        name: 'Close event details',
      }),
    )

    expect(
      screen.queryByRole('dialog'),
    ).not.toBeInTheDocument()
  })
})