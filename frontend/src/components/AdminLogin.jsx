import {
  useState,
} from 'react'

import {
  loginAdmin,
} from '../services/api'


function AdminLogin({ onLogin }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] =
    useState(false)


  async function handleSubmit(event) {
    event.preventDefault()

    setError('')
    setIsSubmitting(true)

    try {
      const result = await loginAdmin(
        username.trim(),
        password,
      )

      onLogin(result)
    } catch (loginError) {
      setError(
        loginError.message ||
          'Administrator sign-in failed.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }


  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <span className="login-shield">
            PS
          </span>

          <div>
            <p className="section-label">
              PROMPTSHIELD
            </p>

            <h1>Administrator sign in</h1>
          </div>
        </div>

        <p className="login-description">
          Sign in to access prompt analysis,
          security events and audit-chain
          verification.
        </p>

        <form
          className="login-form"
          onSubmit={handleSubmit}
        >
          <label>
            <span>Username</span>

            <input
              type="text"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(event) => {
                setUsername(event.target.value)
              }}
              required
              disabled={isSubmitting}
            />
          </label>

          <label>
            <span>Password</span>

            <input
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
              }}
              minLength={8}
              required
              disabled={isSubmitting}
            />
          </label>

          {error && (
            <div
              className="login-error"
              role="alert"
            >
              {error}
            </div>
          )}

          <button
            className="login-submit"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? 'Signing in...'
              : 'Sign in securely'}
          </button>
        </form>

        <p className="login-security-note">
          Credentials are transmitted only to the
          configured PromptShield API. The dashboard
          does not store your password.
        </p>
      </section>
    </main>
  )
}


export default AdminLogin