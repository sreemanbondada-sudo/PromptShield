import { useMemo, useState } from 'react'

function formatLabel(value) {
  if (!value) {
    return 'None'
  }

  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function RecentEvents({ events, onRefresh }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [actionFilter, setActionFilter] = useState('all')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState('')

  const filteredEvents = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase()

    return events.filter((event) => {
      const matchesAction =
        actionFilter === 'all' ||
        event.recommended_action === actionFilter

            const searchableText = [
        event.id,
        event.category,
        event.recommended_action,
        event.risk_level,
        ...(event.sensitive_data_types ?? []),
      ]
        .join(' ')
        .replaceAll('_', ' ')
        .toLowerCase()

      const matchesSearch =
        normalizedSearch === '' ||
        searchableText.includes(normalizedSearch)

      return matchesAction && matchesSearch
    })
  }, [events, searchTerm, actionFilter])

  async function handleRefresh() {
    if (!onRefresh || isRefreshing) {
      return
    }

    setIsRefreshing(true)
    setRefreshError('')

    try {
      await onRefresh()
    } catch {
      setRefreshError(
        'Recent events could not be refreshed.',
      )
    } finally {
      setIsRefreshing(false)
    }
  }

  return (
    <section className="events-section">
      <div className="events-heading">
        <div>
          <p className="section-label">SECURITY ACTIVITY</p>
          <h3>Recent security events</h3>
        </div>

        <button
          type="button"
          className="events-refresh-button"
          onClick={handleRefresh}
          disabled={!onRefresh || isRefreshing}
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh events'}
        </button>
      </div>

      <div className="events-controls">
        <label className="events-search">
          <span>Search events</span>

          <input
            type="search"
            value={searchTerm}
            placeholder="Search category, action or risk"
            onChange={(event) => {
              setSearchTerm(event.target.value)
            }}
          />
        </label>

        <label className="events-filter">
          <span>Filter by action</span>

          <select
            value={actionFilter}
            onChange={(event) => {
              setActionFilter(event.target.value)
            }}
          >
            <option value="all">All actions</option>
            <option value="allow">Allow</option>
            <option value="review">Review</option>
            <option value="redact">Redact</option>
            <option value="block">Block</option>
          </select>
        </label>
      </div>

      <div className="events-summary">
        Showing {filteredEvents.length} of {events.length} events
      </div>

      {refreshError && (
        <p className="events-refresh-error" role="alert">
          {refreshError}
        </p>
      )}

      {events.length === 0 ? (
        <div className="events-empty">
          <p>No security events have been recorded yet.</p>
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="events-empty">
          <p>No events match the selected filters.</p>

          <button
            type="button"
            className="events-clear-button"
            onClick={() => {
              setSearchTerm('')
              setActionFilter('all')
            }}
          >
            Clear filters
          </button>
        </div>
      ) : (
        <div className="events-table-wrapper">
          <table className="events-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Time</th>
                <th>Action</th>
                <th>Risk</th>
                <th>Category</th>
                <th>Sensitive data</th>
              </tr>
            </thead>

            <tbody>
              {filteredEvents.map((event) => (
                <tr key={event.id}>
                  <td>#{event.id}</td>

                  <td>
                    {event.created_at
                      ? new Date(
                          `${event.created_at}Z`,
                        ).toLocaleString()
                      : 'Unknown'}
                  </td>

                  <td>
                    <span
                      className={`event-action action-${event.recommended_action}`}
                    >
                      {formatLabel(
                        event.recommended_action,
                      )}
                    </span>
                  </td>

                  <td>
                    <strong>{event.risk_score}/100</strong>
                    <small>
                      {formatLabel(event.risk_level)}
                    </small>
                  </td>

                  <td>{formatLabel(event.category)}</td>

                  <td>
                    {event.contains_sensitive_data
                      ? 'Detected'
                      : 'None'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default RecentEvents
