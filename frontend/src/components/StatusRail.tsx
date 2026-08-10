import {
  BatteryFull,
  ConnectionSignal,
  Location,
  Time,
} from '@carbon/icons-react'
import type { ReactNode } from 'react'
import type { FlightState } from '../domain/flight-reducer'

function StatusItem({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <span className="status-rail__item">
      <span aria-hidden="true">{icon}</span>
      {children}
    </span>
  )
}

export function StatusRail({ state }: { state: FlightState }) {
  const telemetry = state.telemetry
  const hasGps =
    telemetry !== null &&
    telemetry.latitude !== null &&
    telemetry.longitude !== null
  return (
    <header className="status-rail" aria-label="Flight status">
      <strong>KRTI VTOL</strong>
      <StatusItem icon={<ConnectionSignal size={16} />}>
        <span aria-live="polite">{state.link.toUpperCase()}</span>
      </StatusItem>
      <span>{telemetry?.mode ?? 'NO DATA'}</span>
      <span>{telemetry ? (telemetry.armed ? 'ARMED' : 'DISARMED') : 'NO DATA'}</span>
      <StatusItem icon={<Location size={16} />}>
        <span>{telemetry ? (hasGps ? `GPS ${telemetry.gpsSatellites}` : 'GPS NO FIX') : 'NO DATA'}</span>
      </StatusItem>
      <span>{telemetry ? `ALT ${telemetry.altitudeM.toFixed(1)} m` : 'NO DATA'}</span>
      <span>
        {telemetry?.rangefinderM === null || telemetry === null
          ? 'RANGE NO DATA'
          : `RANGE ${telemetry.rangefinderM.toFixed(1)} m`}
      </span>
      <StatusItem icon={<BatteryFull size={16} />}>
        {telemetry ? `${telemetry.voltage.toFixed(1)} V / ${telemetry.batteryPercent}%` : 'NO DATA'}
      </StatusItem>
      <StatusItem icon={<Time size={16} />}>
        <time>
          {state.lastEventAt === 0
            ? '--:--:--'
            : new Date(state.lastEventAt).toLocaleTimeString('en-GB', {
                hour12: false,
              })}
        </time>
      </StatusItem>
    </header>
  )
}
