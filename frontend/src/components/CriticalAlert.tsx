import { InlineNotification } from '@carbon/react'
import type { FlightState } from '../domain/flight-reducer'

export function CriticalAlert({ state }: { state: FlightState }) {
  const telemetry = state.telemetry
  if (state.safety.elsState === 'active') {
    return (
      <InlineNotification
        hideCloseButton
        kind="error"
        title="ELS ACTIVE"
        subtitle="Emergency landing state reported by the flight controller."
      />
    )
  }
  if (state.link === 'disconnected') {
    return (
      <InlineNotification
        hideCloseButton
        kind="error"
        title={`LINK ${state.link.toUpperCase()}`}
        subtitle={`Lost contact ${state.safety.linkLostSeconds}s. Use RC or physical Emergency Stop.`}
      />
    )
  }
  if (state.safety.obstacleWarning) {
    return (
      <InlineNotification
        hideCloseButton
        kind="error"
        title="Collision clearance low"
        subtitle="Hold position and verify obstacle avoidance."
      />
    )
  }
  if (state.safety.personWarning) {
    return (
      <InlineNotification
        hideCloseButton
        kind="warning"
        title="PERSON IN FLIGHT AREA"
        subtitle="No automatic flight action. Operator must use RC or safety procedure."
      />
    )
  }
  if (!state.camera.connected) {
    return (
      <InlineNotification
        hideCloseButton
        kind="error"
        title="Camera lost"
        subtitle="Reconnecting video stream; flight state remains independent."
      />
    )
  }
  if (telemetry && telemetry.batteryPercent < 20) {
    return (
      <InlineNotification
        hideCloseButton
        kind="error"
        title="Battery critical"
        subtitle="Follow the approved operator emergency procedure."
      />
    )
  }
  if (state.link === 'stale') {
    return (
      <InlineNotification
        hideCloseButton
        kind="warning"
        title="Telemetry stale"
        subtitle="Mission commands are locked."
      />
    )
  }
  return null
}
