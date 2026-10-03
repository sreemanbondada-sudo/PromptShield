import {
  useMemo,
  useState,
} from 'react'

function formatLabel(value) {
  if (!value) {
    return 'None'
  }

  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatTimestamp(value) {
  if (!value) {
    return 'Unknown'
  }

  return new Date(`${value}Z`).toLocaleString()
}

function DetailList({ values, emptyMessage }) {
  if (!values || values.length === 0) {
    return (
      <span className="event-detail-empty">
        {emptyMessage}
      </span>
    )
  }

  return (
    <ul className="event-detail-list">
      {values.map((value) => (
        <li key={value}>{formatLabel(value)}</li>
      ))}
    </ul>
  )
}

function EventDetails({ event, onClose }) {
  return (
    <aside
      className="event-details-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="event-details-title"
    >
      <div className="event-details-header">
        <div>
          <p className="section-label">
            EVENT INVESTIGATION
          </p>

          <h4 id="event-details-title">
            Security event #{event.id}
          </h4>
        </div>

        <button
          type="button"
          className="event-details-close"
          onClick={onClose}
          aria-label="Close event details"
        >
          Close
        </button>
      </div>

      <div className="event-details-grid">
        <div>
          <span>Recorded at</span>
          <strong>
            {formatTimestamp(event.created_at)}
          </strong>
        </div>

        <div>
          <span>Recommended action</span>
          <strong>
            {formatLabel(event.recommended_action)}
          </strong>
        </div>

        <div>
          <span>Risk score</span>
          <strong>{event.risk_score}/100</strong>
        </div>

        <div>
          <span>Risk level</span>
          <strong>
            {formatLabel(event.risk_level)}
          </strong>
        </div>

        <div>
          <span>Category</span>
          <strong>
            {formatLabel(event.category)}
          </strong>
        </div>

        <div>
          <span>Malicious classification</span>
          <strong>
            {event.is_malicious
              ? 'Detected'
              : 'Not detected'}
          </strong>
        </div>

        <div>
          <span>Sensitive data</span>
          <strong>
            {event.contains_sensitive_data
              ? 'Detected'
              : 'Not detected'}
          </strong>
        </div>

        <div>
          <span>Prompt length</span>
          <strong>
            {event.prompt_length} characters
          </strong>
        </div>
      </div>

      <div className="event-detail-section">
        <h5>Matched security patterns</h5>

        <DetailList
          values={event.matched_patterns}
          emptyMessage="No rule patterns matched."
        />
      </div>

      <div className="event-detail-section">
        <h5>Sensitive-data types</h5>

        <DetailList
          values={event.sensitive_data_types}
          emptyMessage={
            'No sensitive-data types were detected.'
          }
        />
      </div>

      <div className="event-detail-section">
        <h5>Audit-chain metadata</h5>

        <div className="event-hash">
          <span>Previous hash</span>
          <code>
            {event.previous_hash ?? 'Unavailable'}
          </code>
        </div>

        <div className="event-hash">
          <span>Event hash</span>
          <code>
            {event.event_hash ?? 'Unavailable'}
          </code>
        </div>
      </div>

      <p className="event-privacy-note">
        PromptShield displays security metadata only.
        Original prompt contents are not exposed through
        this event view.
      </p>
    </aside>
  )
}

function RecentEvents({ events, onRefresh }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [actionFilter, setActionFilter] = useState('all')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState('')
  const [selectedEvent, setSelectedEvent] = useState(null)

  const filteredEvents = useMemo(() => {
    const normalizedSearch = searchTerm
      .trim()
      .toLowerCase()

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
          <p className="section-label">
            SECURITY ACTIVITY
          </p>

          <h3>Recent security events</h3>
        </div>

        <button
          type="button"
          className="events-refresh-button"
          onClick={handleRefresh}
          disabled={!onRefresh || isRefreshing}
        >
          {isRefreshing
            ? 'Refreshing...'
            : 'Refresh events'}
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
        Showing {filteredEvents.length} of {events.length}{' '}
        events
      </div>

      {refreshError && (
        <p
          className="events-refresh-error"
          role="alert"
        >
          {refreshError}
        </p>
      )}

      {selectedEvent && (
        <EventDetails
          event={selectedEvent}
          onClose={() => {
            setSelectedEvent(null)
          }}
        />
      )}

      {events.length === 0 ? (
        <div className="events-empty">
          <p>
            No security events have been recorded yet.
          </p>
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="events-empty">
          <p>
            No events match the selected filters.
          </p>

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
                <th>Investigation</th>
              </tr>
            </thead>

            <tbody>
              {filteredEvents.map((event) => (
                <tr key={event.id}>
                  <td>#{event.id}</td>

                  <td>
                    {formatTimestamp(event.created_at)}
                  </td>

                  <td>
                    <span
                      className={
                        `event-action ` +
                        `action-${event.recommended_action}`
                      }
                    >
                      {formatLabel(
                        event.recommended_action,
                      )}
                    </span>
                  </td>

                  <td>
                    <strong>
                      {event.risk_score}/100
                    </strong>

                    <small>
                      {formatLabel(event.risk_level)}
                    </small>
                  </td>

                  <td>
                    {formatLabel(event.category)}
                  </td>

                  <td>
                    {event.contains_sensitive_data
                      ? 'Detected'
                      : 'None'}
                  </td>

                  <td>
                    <button
                      type="button"
                      className="event-view-button"
                      aria-label={
                        `View details for event #${event.id}`
                      }
                      onClick={() => {
                        setSelectedEvent(event)
                      }}
                    >
                      View details
                    </button>
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
