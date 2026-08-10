import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CriticalAlert } from '../components/CriticalAlert'
import { initialFlightState } from '../domain/flight-reducer'

describe('VTOL critical alerts', () => {
  it('prioritizes backend ELS active over lower severity events', () => {
    render(
      <CriticalAlert
        state={{
          ...initialFlightState,
          link: 'disconnected',
          safety: {
            ...initialFlightState.safety,
            elsState: 'active',
            linkLostSeconds: 16,
            personWarning: true,
          },
        }}
      />,
    )
    expect(screen.getByText('ELS ACTIVE')).toBeVisible()
    expect(screen.queryByText('PERSON IN FLIGHT AREA')).not.toBeInTheDocument()
  })

  it('renders passive person warning without creating an action', () => {
    render(
      <CriticalAlert
        state={{
          ...initialFlightState,
          link: 'connected',
          camera: { id: 'front', connected: true, fps: 24, latencyMs: 112 },
          safety: { ...initialFlightState.safety, personWarning: true },
        }}
      />,
    )
    expect(screen.getByText('PERSON IN FLIGHT AREA')).toBeVisible()
    expect(screen.getByText(/No automatic flight action/)).toBeVisible()
  })

  it('does not warn critically for GPS no-fix alone', () => {
    render(
      <CriticalAlert
        state={{
          ...initialFlightState,
          link: 'connected',
          camera: { id: 'front', connected: true, fps: 24, latencyMs: 112 },
          telemetry: {
            type: 'telemetry',
            seq: 1,
            timestampMs: 1,
            armed: true,
            mode: 'AUTO',
            batteryPercent: 72,
            voltage: 15.9,
            latitude: null,
            longitude: null,
            gpsFix: 0,
            gpsSatellites: 0,
            hdop: null,
            localXM: 1,
            localYM: 1,
            altitudeM: 1,
            rangefinderM: 1,
            groundSpeedMps: 0,
            headingDeg: 0,
            rollDeg: 0,
            pitchDeg: 0,
            yawDeg: 0,
            collisionClearanceM: 4,
          },
        }}
      />,
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
