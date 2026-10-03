import {
  useCallback,
  useEffect,
  useState,
} from 'react'
import './App.css'
import RecentEvents from './components/RecentEvents'
import SecurityBreakdown from './components/SecurityBreakdown'
import {
  analyzePrompt,
  checkApiHealth,
  getRecentEvents,
  getStatistics,
  verifyAuditChain,
} from './services/api'

function formatLabel(value) {
  if (!value) {
    return 'None'
  }

  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function App() {
  const [prompt, setPrompt] = useState('')
  const [apiStatus, setApiStatus] = useState('checking')
  const [analysis, setAnalysis] = useState(null)
  const [recentEvents, setRecentEvents] = useState([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [statistics, setStatistics] = useState(null)
  const [auditStatus, setAuditStatus] = useState(null)

  const loadDashboardSummary = useCallback(async () => {
  const [
    statisticsResult,
    auditResult,
    eventsResult,
  ] = await Promise.allSettled([
    getStatistics(),
    verifyAuditChain(),
    getRecentEvents(10),
  ])

  if (statisticsResult.status === 'fulfilled') {
    setStatistics(statisticsResult.value)
  }

  if (auditResult.status === 'fulfilled') {
    setAuditStatus(auditResult.value)
  }

  if (eventsResult.status === 'fulfilled') {
    setRecentEvents(eventsResult.value.events)
  }
}, [])

  useEffect(() => {
    let isMounted = true

    async function loadInitialData() {
      try {
        const result = await checkApiHealth()

        if (isMounted && result.status === 'healthy') {
          setApiStatus('online')
        }
      } catch {
        if (isMounted) {
          setApiStatus('offline')
        }
      }

      if (isMounted) {
        await loadDashboardSummary()
      }
    }

    loadInitialData()

    return () => {
      isMounted = false
    }
  }, [loadDashboardSummary])

  async function handleSubmit(event) {
    event.preventDefault()

    const trimmedPrompt = prompt.trim()

    if (!trimmedPrompt || isAnalyzing) {
      return
    }

    setIsAnalyzing(true)
    setError('')
    setAnalysis(null)

    try {
      const result = await analyzePrompt(trimmedPrompt)
      setAnalysis(result)
      await loadDashboardSummary()
    } catch (requestError) {
      setError(
        requestError.message ||
          'Prompt analysis failed. Please try again.',
      )
    } finally {
      setIsAnalyzing(false)
    }
  }

  function handleClear() {
    setPrompt('')
    setAnalysis(null)
    setError('')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            PS
          </div>

          <div>
            <h1>PromptShield</h1>
            <p>AI Prompt Security Gateway</p>
          </div>
        </div>

        <div className="system-status">
          <span className={`status-dot ${apiStatus}`} />

          {apiStatus === 'online' && 'API online'}
          {apiStatus === 'offline' && 'API unavailable'}
          {apiStatus === 'checking' && 'Checking API'}
        </div>
      </header>

      <main className="dashboard">
        <section className="hero-section">
          <div>
            <p className="eyebrow">REAL-TIME AI SECURITY</p>

            <h2>
              Analyze prompts before they reach your AI application.
            </h2>

            <p className="hero-description">
              Detect prompt injection, sensitive-data exposure and
              suspicious machine-learning patterns through one
              explainable security gateway.
            </p>
          </div>

          <div className="protection-summary">
            <span>Rule engine</span>
            <span>Sensitive-data detection</span>
            <span>ML classification</span>
          </div>
        </section>

        <section className="analysis-grid">
          <article className="panel prompt-panel">
            <div className="panel-heading">
              <div>
                <p className="section-label">PROMPT ANALYSIS</p>
                <h3>Inspect a user prompt</h3>
              </div>

              <span className="character-count">
                {prompt.length}/5000
              </span>
            </div>

            <form onSubmit={handleSubmit}>
              <label htmlFor="prompt">
                Prompt to analyze
              </label>

              <textarea
                id="prompt"
                value={prompt}
                maxLength={5000}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="Enter a prompt to inspect for security risks..."
                disabled={isAnalyzing}
              />

              {error && (
                <div className="error-message" role="alert">
                  {error}
                </div>
              )}

              <div className="form-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={handleClear}
                  disabled={!prompt && !analysis && !error}
                >
                  Clear
                </button>

                <button
                  className="primary-button"
                  type="submit"
                  disabled={!prompt.trim() || isAnalyzing}
                >
                  {isAnalyzing
                    ? 'Analyzing...'
                    : 'Analyze prompt'}
                </button>
              </div>
            </form>
          </article>

          <article className="panel result-panel">
            <p className="section-label">ANALYSIS RESULT</p>

            {!analysis && !isAnalyzing && (
              <div className="empty-result">
                <div className="shield-icon" aria-hidden="true">
                  ✓
                </div>

                <h3>Ready to inspect</h3>

                <p>
                  Submit a prompt to view its verdict, risk score,
                  attack category, ML probability and recommended
                  action.
                </p>
              </div>
            )}

            {isAnalyzing && (
              <div className="empty-result" aria-live="polite">
                <div className="loading-spinner" />

                <h3>Analyzing prompt</h3>

                <p>
                  PromptShield is running its security detectors.
                </p>
              </div>
            )}

            {analysis && !isAnalyzing && (
              <div className="analysis-result">
                <div
                  className={`verdict verdict-${analysis.recommended_action}`}
                >
                  <span>Recommended action</span>

                  <strong>
                    {formatLabel(
                      analysis.recommended_action,
                    )}
                  </strong>
                </div>

                <div className="result-metrics">
                  <div>
                    <span>Risk score</span>
                    <strong>{analysis.risk_score}/100</strong>
                  </div>

                  <div>
                    <span>Risk level</span>
                    <strong>
                      {formatLabel(analysis.risk_level)}
                    </strong>
                  </div>

                  <div>
                    <span>Category</span>
                    <strong>
                      {formatLabel(analysis.category)}
                    </strong>
                  </div>

                  <div>
                    <span>ML probability</span>
                    <strong>
                      {Math.round(
                        (analysis.ml_probability ?? 0) * 100,
                      )}
                      %
                    </strong>
                  </div>
                </div>

                <div className="result-section">
                  <span>Explanation</span>
                  <p>{analysis.explanation}</p>
                </div>

                <div className="result-section">
                  <span>Detection sources</span>

                  <div className="tag-list">
                    {analysis.detection_sources?.length > 0 ? (
                      analysis.detection_sources.map((source) => (
                        <span className="tag" key={source}>
                          {formatLabel(source)}
                        </span>
                      ))
                    ) : (
                      <span className="muted-text">
                        No detector raised an alert
                      </span>
                    )}
                  </div>
                </div>

                {analysis.matched_patterns?.length > 0 && (
                  <div className="result-section">
                    <span>Matched security patterns</span>

                    <div className="tag-list">
                      {analysis.matched_patterns.map((pattern) => (
                        <span
                          className="tag warning-tag"
                          key={pattern}
                        >
                          {formatLabel(pattern)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.contains_sensitive_data && (
                  <div className="result-section">
                    <span>Protected prompt preview</span>

                    <p className="redacted-preview">
                      {analysis.redacted_prompt}
                    </p>
                  </div>
                )}

                <p className="event-reference">
                  Security event #{analysis.event_id}
                </p>
              </div>
            )}
          </article>
        </section>

        <section
          className="statistics-grid"
          aria-label="Security statistics"
        >
          <article className="stat-card">
            <p>Total scans</p>
            <strong>
              {statistics?.total_scans ?? '—'}
            </strong>
            <span>Prompts analyzed by PromptShield</span>
          </article>

          <article className="stat-card">
            <p>Malicious prompts</p>
            <strong>
              {statistics?.malicious_prompts ?? '—'}
            </strong>
            <span>Rule-confirmed security threats</span>
          </article>

          <article className="stat-card">
            <p>Sensitive prompts</p>
            <strong>
              {statistics?.sensitive_prompts ?? '—'}
            </strong>
            <span>Prompts requiring data protection</span>
          </article>

          <article
            className={`stat-card audit-card ${
              auditStatus?.valid
                ? 'audit-valid'
                : 'audit-unavailable'
            }`}
          >
            <p>Audit integrity</p>

            <strong>
              {auditStatus
                ? auditStatus.valid
                  ? 'Verified'
                  : 'Broken'
                : '—'}
            </strong>

            <span>
              {auditStatus
                ? `${auditStatus.checked_events} events checked`
                : 'Verification unavailable'}
            </span>
          </article>
            </section>
                        <SecurityBreakdown statistics={statistics} />
        <RecentEvents events={recentEvents} />
      </main>
    </div>
  )
}

export default App

