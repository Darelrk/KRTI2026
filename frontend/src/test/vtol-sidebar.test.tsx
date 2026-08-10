import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MissionProgress } from '../components/MissionProgress'
import { PayloadStatus } from '../components/PayloadStatus'
import { PositionTelemetry } from '../components/PositionTelemetry'
import { SafetyEventQueue } from '../components/SafetyEventQueue'
import type { TelemetryEvent } from '../domain/flight'
import { initialFlightState } from '../domain/flight-reducer'

const telemetry: TelemetryEvent = {
  type: 'telemetry',
  seq: 1,
  timestampMs: 1_000,
  armed: true,
  mode: 'AUTO',
  batteryPercent: 72,
  voltage: 15.9,
  latitude: -7.7706,
  longitude: 110.3776,
  gpsFix: 3,
  gpsSatellites: 12,
  hdop: 0.8,
  localXM: 12.5,
  localYM: 8.25,
  altitudeM: 6.4,
  rangefinderM: 5.9,
  groundSpeedMps: 2.3,
  headingDeg: 91,
  rollDeg: 1.2,
  pitchDeg: -0.7,
  yawDeg: 91,
  collisionClearanceM: 3.8,
}

describe('VTOL mission sidebar', () => {
  it('shows all five scored missions, remaining time, and retry checkpoint', () => {
    render(
      <MissionProgress
        mission={{
          ...initialFlightState.mission,
          phase: 3,
          phaseName: 'Triple gate navigation',
          waypointLabel: 'WP2',
          status: 'retry',
          elapsedSeconds: 125,
          score: 30,
          retryCheckpoint: 'WP2',
        }}
      />,
    )
    expect(screen.getAllByRole('listitem')).toHaveLength(5)
    for (const score of ['10 pts', '40 pts', '20 pts', '15 pts']) {
      expect(screen.getAllByText(score).length).toBeGreaterThan(0)
    }
    expect(screen.getByText('07:55')).toBeVisible()
    expect(screen.getByText('RETRY → WP2')).toBeVisible()
    expect(screen.getByText('30 / 100')).toBeVisible()
  })

  it('shows global, local, altitude, range, speed, and attitude telemetry', () => {
    render(<PositionTelemetry telemetry={telemetry} />)
    expect(screen.getByText('LAT -7.770600')).toBeVisible()
    expect(screen.getByText('LON 110.377600')).toBeVisible()
    expect(screen.getByText('LOCAL X 12.50 m')).toBeVisible()
    expect(screen.getByText('LOCAL Y 8.25 m')).toBeVisible()
    expect(screen.getByText('ALT 6.4 m')).toBeVisible()
    expect(screen.getByText('RANGE 5.9 m')).toBeVisible()
    expect(screen.getByText('HDG 091°')).toBeVisible()
    expect(screen.getByText('ROLL +1.2°')).toBeVisible()
    expect(screen.getByText('PITCH -0.7°')).toBeVisible()
    expect(screen.getByText('YAW 091°')).toBeVisible()
  })

  it('renders missing position sources as no data instead of zero', () => {
    render(
      <PositionTelemetry
        telemetry={{
          ...telemetry,
          latitude: null,
          longitude: null,
          hdop: null,
          localXM: null,
          localYM: null,
          rangefinderM: null,
        }}
      />,
    )
    expect(screen.getByText('GPS NO FIX')).toBeVisible()
    expect(screen.getAllByText(/NO DATA/).length).toBeGreaterThanOrEqual(3)
    expect(screen.queryByText(/0\.000000/)).not.toBeInTheDocument()
  })

  it('shows payload state as an explicit label', () => {
    render(<PayloadStatus state="released" />)
    expect(screen.getByText('RELEASED')).toBeVisible()
    expect(screen.getByText('Medical payload')).toBeVisible()
  })

  it('acknowledges person warnings without issuing flight commands', () => {
    const acknowledge = vi.fn()
    render(
      <SafetyEventQueue
        link="connected"
        safety={{
          ...initialFlightState.safety,
          personWarning: true,
          personAcknowledged: false,
        }}
        onAcknowledgePerson={acknowledge}
      />,
    )
    expect(screen.getByText('PERSON IN FLIGHT AREA')).toBeVisible()
    fireEvent.click(
      screen.getByRole('button', { name: 'Acknowledge person warning' }),
    )
    expect(acknowledge).toHaveBeenCalledOnce()
  })
})
