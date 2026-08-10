import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { NavigationMap } from '../components/NavigationMap'
import type { RouteMarker } from '../components/NavigationMap'
import type { TelemetryEvent } from '../domain/flight'
import type {
  MissionSite,
  OverlayCalibration,
} from '../domain/mission-map'
import { initialFlightState } from '../domain/flight-reducer'

const site: MissionSite = {
  name: 'Mock VTOL site',
  center: { latitude: -7.7706, longitude: 110.3776 },
  courseReference: { x: 50, y: 50 },
  metersPerUnit: { x: 0.8, y: 0.6 },
  courseUpBearingDeg: 20,
}

const calibration: OverlayCalibration = {
  courseAnchor: { x: 50, y: 50 },
  mapAnchor: { x: 50, y: 50 },
  scaleX: 0.5,
  scaleY: -0.5,
  rotationDeg: 0,
}

const route: RouteMarker[] = [
  { id: 'start', kind: 'start', point: { x: 45, y: 55 } },
  { id: 'wp1', kind: 'waypoint', point: { x: 50, y: 50 } },
  { id: 'gate', kind: 'gate', point: { x: 55, y: 45 } },
  { id: 'drop', kind: 'drop_zone', point: { x: 60, y: 40 } },
  { id: 'land', kind: 'landing_pad', point: { x: 65, y: 35 } },
]

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

const baseProps = {
  telemetry,
  track: [{ latitude: -7.7707, longitude: 110.3775 }],
  mission: initialFlightState.mission,
  site,
  route,
  calibration,
  baseMapAvailable: true,
}

describe('NavigationMap', () => {
  it('renders the KKI-style satellite map, route, and VTOL position', () => {
    render(<NavigationMap {...baseProps} />)
    expect(screen.getByTitle('VTOL satellite base map')).toHaveAttribute(
      'src',
      expect.stringContaining('maps.google.com/maps'),
    )
    expect(screen.getByLabelText('VTOL position marker')).toHaveAttribute(
      'data-course-heading',
      '91',
    )
    expect(screen.getByLabelText('VTOL mission route')).toBeVisible()
    expect(screen.getByText(/7\.770600° S/)).toBeVisible()
    expect(screen.getByText(/110\.377600° E/)).toBeVisible()
  })

  it('keeps the route visible while waiting for a GPS fix', () => {
    render(
      <NavigationMap
        {...baseProps}
        telemetry={null}
        track={[]}
      />,
    )
    expect(screen.getByText('WAITING FOR GPS FIX')).toBeVisible()
    expect(screen.getByLabelText('VTOL mission route')).toBeVisible()
  })

  it('recenters to the latest telemetry only after refresh', () => {
    const { rerender } = render(<NavigationMap {...baseProps} />)
    const original = screen.getByTitle('VTOL satellite base map').getAttribute('src')
    const latest = { ...telemetry, latitude: -7.771, longitude: 110.378 }
    rerender(<NavigationMap {...baseProps} telemetry={latest} />)
    expect(screen.getByTitle('VTOL satellite base map')).toHaveAttribute(
      'src',
      original,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Refresh map' }))
    expect(screen.getByTitle('VTOL satellite base map').getAttribute('src')).toContain(
      'll=-7.771%2C110.378',
    )
  })

  it('keeps the SVG overlay when satellite imagery is unavailable', () => {
    render(<NavigationMap {...baseProps} baseMapAvailable={false} />)
    expect(screen.queryByTitle('VTOL satellite base map')).not.toBeInTheDocument()
    expect(screen.getByText('SATELLITE MAP UNAVAILABLE')).toBeVisible()
    expect(screen.getByLabelText('VTOL mission route')).toBeVisible()
  })
})
