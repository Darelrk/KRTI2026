import { useMutation, useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useReducer, useState } from 'react'
import { backendFlightAdapter } from '../data/backend-flight-adapter'
import { mockFlightAdapter } from '../data/mock-flight-adapter'
import { initialFlightState, reduceFlightEvent } from '../domain/flight-reducer'

function sessionAdapter() {
  const hasScenario =
    typeof window !== 'undefined' &&
    new URLSearchParams(window.location.search).has('scenario')
  return backendFlightAdapter && !hasScenario
    ? backendFlightAdapter
    : mockFlightAdapter
}

export function useFlightSession() {
  const adapter = sessionAdapter()
  const snapshot = useQuery({
    queryKey: ['flight', 'snapshot'],
    queryFn: () => adapter.getSnapshot(),
  })
  const [state, dispatch] = useReducer(reduceFlightEvent, initialFlightState)
  const [now, setNow] = useState(Date.now)

  useEffect(() => adapter.subscribe(dispatch), [adapter])
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1_000)
    return () => window.clearInterval(timer)
  }, [])

  const command = useMutation({
    mutationFn: (request: Parameters<typeof adapter.sendCommand>[0]) =>
      adapter.sendCommand(request),
  })
  const current =
    state.lastEventAt === 0 && snapshot.data ? snapshot.data : state
  const liveState =
    current.link === 'connected' && now - current.lastEventAt > 2_000
      ? { ...current, link: 'stale' as const }
      : current
  const acknowledgePersonWarning = useCallback(() => {
    dispatch({ type: 'ack_person_warning' })
  }, [])

  return { state: liveState, command, acknowledgePersonWarning }
}
