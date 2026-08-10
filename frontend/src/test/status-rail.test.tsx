import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { StatusRail } from '../components/StatusRail'
import { initialFlightState } from '../domain/flight-reducer'

it('renders the VTOL identity and stable no-data status before telemetry hydrates', () => {
  render(<StatusRail state={initialFlightState} />)
  expect(screen.getByText('KRTI VTOL')).toBeVisible()
  expect(screen.getAllByText('NO DATA').length).toBeGreaterThan(0)
  expect(screen.getByText('--:--:--')).toBeVisible()
})

it('renders complete VTOL telemetry fields without relying on GPS for mode', () => {
  render(
    <StatusRail
      state={{
        ...initialFlightState,
        link: 'connected',
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
        },
      }}
    />,
  )
  expect(screen.getByText('AUTO')).toBeVisible()
  expect(screen.getByText('ARMED')).toBeVisible()
  expect(screen.getByText('ALT 6.4 m')).toBeVisible()
  expect(screen.getByText('RANGE 5.9 m')).toBeVisible()
  expect(screen.getByText('GPS NO FIX')).toBeVisible()
})
