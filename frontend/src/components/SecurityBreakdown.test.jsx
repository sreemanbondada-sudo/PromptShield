import {
  render,
  screen,
} from '@testing-library/react'
import {
  describe,
  expect,
  test,
} from 'vitest'

import SecurityBreakdown from './SecurityBreakdown'

describe('SecurityBreakdown', () => {
  test('shows empty states when no statistics exist', () => {
    render(<SecurityBreakdown statistics={null} />)

    expect(
      screen.getAllByText(
        'No activity is available yet.',
      ),
    ).toHaveLength(2)
  })

  test('renders action and category totals', () => {
    const statistics = {
      actions: {
        allow: 6,
        review: 2,
        redact: 3,
        block: 4,
      },
      categories: {
        safe: 6,
        prompt_injection: 4,
        sensitive_data_exposure: 3,
        ml_suspicious_prompt: 2,
      },
    }

    render(
      <SecurityBreakdown statistics={statistics} />,
    )

    expect(screen.getByText('Allow')).toBeInTheDocument()
    expect(screen.getByText('Review')).toBeInTheDocument()
    expect(screen.getByText('Redact')).toBeInTheDocument()
    expect(screen.getByText('Block')).toBeInTheDocument()

    expect(
      screen.getByText('Prompt Injection'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Sensitive Data Exposure'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Ml Suspicious Prompt'),
    ).toBeInTheDocument()
  })

  test('scales bars relative to the largest value', () => {
    const statistics = {
      actions: {
        allow: 10,
        block: 5,
      },
      categories: {},
    }

    const { container } = render(
      <SecurityBreakdown statistics={statistics} />,
    )

    const bars = container.querySelectorAll(
      '.breakdown-bar',
    )

    expect(bars[0]).toHaveStyle({
      width: '100%',
    })

    expect(bars[1]).toHaveStyle({
      width: '50%',
    })
  })
})