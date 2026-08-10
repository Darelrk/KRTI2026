import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { NavigationMap } from '../components/NavigationMap'
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
  mission: initialFlightState.mission,
  site,
  calibration,
  baseMapAvailable: true,
}

describe('NavigationMap', () => {
  it('renders the satellite map and VTOL drone position', () => {
    render(<NavigationMap {...baseProps} />)
    expect(screen.getByTitle('VTOL satellite base map')).toHaveAttribute(
      'src',
      expect.stringContaining('maps.google.com/maps'),
    )
    expect(screen.getByTitle('VTOL satellite base map')).toHaveAttribute(
      'src',
      expect.stringContaining('z=16'),
    )
    expect(screen.getByLabelText('VTOL position marker')).toHaveAttribute(
      'data-course-heading',
      '91',
    )
    expect(screen.queryByLabelText('VTOL mission route')).not.toBeInTheDocument()
    expect(screen.getByText(/7\.770600° S/)).toBeVisible()
    expect(screen.getByText(/110\.377600° E/)).toBeVisible()
  })

  it('keeps the satellite map visible while waiting for GPS', () => {
    render(
      <NavigationMap
        {...baseProps}
        telemetry={null}
      />,
    )
    expect(screen.getByTitle('VTOL satellite base map')).toBeVisible()
    expect(screen.queryByLabelText('VTOL position marker')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('VTOL mission route')).not.toBeInTheDocument()
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

  it('does not render the SVG route overlay when satellite imagery is unavailable', () => {
    render(<NavigationMap {...baseProps} baseMapAvailable={false} />)
    expect(screen.queryByTitle('VTOL satellite base map')).not.toBeInTheDocument()
    expect(screen.getByText('SATELLITE MAP UNAVAILABLE')).toBeVisible()
    expect(screen.queryByLabelText('VTOL mission route')).not.toBeInTheDocument()
  })
})
