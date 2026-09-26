export default function TimetableCard({ invocationResult }) {
  if (!invocationResult.success) {
    return (
      <div className="tool-card tool-card-error">
        {invocationResult.error || 'No timetable information found.'}
      </div>
    )
  }

  return (
    <div className="tool-card">
      <div className="tool-card-title">Timetable — {invocationResult.course_code}</div>
      <table className="timetable-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Time</th>
            <th>Venue</th>
          </tr>
        </thead>
        <tbody>
          {invocationResult.sessions.map((session, i) => (
            <tr key={i}>
              <td>{session.date}</td>
              <td>{session.start_time}–{session.end_time}</td>
              <td>{session.venue}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
