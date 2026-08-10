import type { FlightState } from '../domain/flight-reducer'

const missions = [
  { phase: 1, name: 'Manual & transition', score: 10 },
  { phase: 2, name: 'Medical delivery', score: 40 },
  { phase: 3, name: 'Triple gate', score: 20 },
  { phase: 4, name: 'Vision line tracking', score: 15 },
  { phase: 5, name: 'Final gate & landing', score: 15 },
] as const

function formatTime(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = String(totalSeconds % 60).padStart(2, '0')
  return `${String(minutes).padStart(2, '0')}:${seconds}`
}

export function MissionProgress({
  mission,
}: {
  mission: FlightState['mission']
}) {
  const remainingSeconds = Math.max(0, 600 - mission.elapsedSeconds)
  return (
    <section
      className="mission-progress"
      aria-labelledby="mission-progress-title"
    >
      <header className="mission-progress__header">
        <div>
          <span>Mission sequence</span>
          <h2 id="mission-progress-title">VTOL progress</h2>
        </div>
        <time>{formatTime(remainingSeconds)}</time>
      </header>
      <div className="mission-progress__summary">
        <strong>{mission.score} / 100</strong>
        <span>{mission.waypointLabel}</span>
        {mission.status === 'retry' && (
          <span>RETRY → {mission.retryCheckpoint}</span>
        )}
      </div>
      <ol className="mission-progress__list">
        {missions.map((item) => (
          <li
            key={item.phase}
            className={
              item.phase === mission.phase
                ? 'mission-progress__phase--active'
                : item.phase < mission.phase
                  ? 'mission-progress__phase--passed'
                  : undefined
            }
          >
            <span>M{item.phase}</span>
            <strong>{item.name}</strong>
            <span>{item.score} pts</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
