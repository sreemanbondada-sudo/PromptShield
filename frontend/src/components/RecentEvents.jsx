function formatLabel(value) {
  if (!value) {
    return 'None'
  }

  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function RecentEvents({ events }) {
  return (
    <section className="events-section">
      <div className="events-heading">
        <div>
          <p className="section-label">SECURITY ACTIVITY</p>
          <h3>Recent security events</h3>
        </div>

        <span>
          Showing {events.length} recent events
        </span>
      </div>

      {events.length === 0 ? (
        <div className="events-empty">
          <p>No security events have been recorded yet.</p>
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
              {events.map((event) => (
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