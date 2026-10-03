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

import AdminLogin from './AdminLogin'
import {
  loginAdmin,
} from '../services/api'


vi.mock('../services/api', () => ({
  loginAdmin: vi.fn(),
}))


describe('AdminLogin', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })


  test('renders administrator credentials fields', () => {
    render(
      <AdminLogin onLogin={vi.fn()} />,
    )

    expect(
      screen.getByRole('heading', {
        name: 'Administrator sign in',
      }),
    ).toBeInTheDocument()

    expect(
      screen.getByLabelText('Username'),
    ).toHaveValue('admin')

    expect(
      screen.getByLabelText('Password'),
    ).toHaveAttribute('type', 'password')
  })


  test('submits credentials and completes login', async () => {
    const user = userEvent.setup()
    const onLogin = vi.fn()

    const loginResult = {
      access_token: 'test-access-token',
      token_type: 'bearer',
      expires_in: 1800,
    }

    loginAdmin.mockResolvedValue(loginResult)

    render(
      <AdminLogin onLogin={onLogin} />,
    )

    await user.type(
      screen.getByLabelText('Password'),
      'correct-test-password',
    )

    await user.click(
      screen.getByRole('button', {
        name: 'Sign in securely',
      }),
    )

    await waitFor(() => {
      expect(loginAdmin).toHaveBeenCalledWith(
        'admin',
        'correct-test-password',
      )
    })

    expect(onLogin).toHaveBeenCalledWith(
      loginResult,
    )
  })


  test('shows a safe authentication error', async () => {
    const user = userEvent.setup()

    loginAdmin.mockRejectedValue(
      new Error(
        'Invalid administrator credentials.',
      ),
    )

    render(
      <AdminLogin onLogin={vi.fn()} />,
    )

    await user.type(
      screen.getByLabelText('Password'),
      'incorrect-password',
    )

    await user.click(
      screen.getByRole('button', {
        name: 'Sign in securely',
      }),
    )

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent(
      'Invalid administrator credentials.',
    )
  })
})