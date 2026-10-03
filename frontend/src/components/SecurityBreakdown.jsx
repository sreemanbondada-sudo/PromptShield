function formatLabel(value) {
  if (!value) {
    return 'None'
  }

  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function BreakdownList({
  title,
  description,
  values,
}) {
  const entries = Object.entries(values ?? {})
    .sort((first, second) => second[1] - first[1])

  const maximumValue = Math.max(
    ...entries.map(([, count]) => count),
    1,
  )

  return (
    <article className="breakdown-card">
      <div>
        <p className="section-label">{title}</p>
        <p className="breakdown-description">
          {description}
        </p>
      </div>

      {entries.length === 0 ? (
        <p className="breakdown-empty">
          No activity is available yet.
        </p>
      ) : (
        <div className="breakdown-list">
          {entries.map(([label, count]) => (
            <div className="breakdown-item" key={label}>
              <div className="breakdown-label">
                <span>{formatLabel(label)}</span>
                <strong>{count}</strong>
              </div>

              <div className="breakdown-track">
                <div
                  className="breakdown-bar"
                  style={{
                    width: `${(count / maximumValue) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  )
}

function SecurityBreakdown({ statistics }) {
  return (
    <section
      className="breakdown-grid"
      aria-label="Security activity breakdown"
    >
      <BreakdownList
        title="ACTIONS"
        description="Decisions produced by the hybrid security engine."
        values={statistics?.actions}
      />

      <BreakdownList
        title="CATEGORIES"
        description="Most frequently detected prompt classifications."
        values={statistics?.categories}
      />
    </section>
  )
}

export default SecurityBreakdown