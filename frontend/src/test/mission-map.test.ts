import { describe, expect, it } from 'vitest'
import {
  buildGoogleMapsSatelliteEmbedUrl,
  courseHeadingToOverlay,
  coursePointToGeo,
  coursePointToOverlay,
  geoPointToCourse,
} from '../domain/mission-map'
import type {
  MissionSite,
  OverlayCalibration,
} from '../domain/mission-map'

const site: MissionSite = {
  name: 'Mock VTOL site',
  center: { latitude: -7.7706, longitude: 110.3776 },
  courseReference: { x: 50, y: 50 },
  metersPerUnit: { x: 0.8, y: 0.6 },
  courseUpBearingDeg: 20,
}

const calibration: OverlayCalibration = {
  courseAnchor: { x: 50, y: 50 },
  mapAnchor: { x: 52, y: 48 },
  scaleX: 0.8,
  scaleY: -0.6,
  rotationDeg: -12,
}

describe('VTOL mission site projection', () => {
  it('maps the course reference to the configured GPS center', () => {
    expect(coursePointToGeo(site.courseReference, site)).toEqual(site.center)
  })

  it('round-trips local course coordinates through GPS', () => {
    const point = { x: 64, y: 37 }
    const restored = geoPointToCourse(coursePointToGeo(point, site), site)
    expect(restored.x).toBeCloseTo(point.x, 6)
    expect(restored.y).toBeCloseTo(point.y, 6)
  })

  it('anchors and mirrors calibrated overlay points', () => {
    expect(coursePointToOverlay(calibration.courseAnchor, calibration)).toEqual(
      calibration.mapAnchor,
    )
    expect(
      coursePointToOverlay({ x: 50, y: 60 }, calibration).y,
    ).toBeLessThan(calibration.mapAnchor.y)
  })

  it('transforms opposite headings to remain 180 degrees apart', () => {
    const north = courseHeadingToOverlay(0, calibration)
    const south = courseHeadingToOverlay(180, calibration)
    const difference = Math.abs(north - south)
    expect(Math.min(difference, 360 - difference)).toBeCloseTo(180, 6)
  })

  it('builds a pin-free Google satellite embed URL', () => {
    const url = new URL(buildGoogleMapsSatelliteEmbedUrl(site.center))
    expect(url.origin).toBe('https://maps.google.com')
    expect(url.pathname).toBe('/maps')
    expect(url.searchParams.get('ll')).toBe('-7.7706,110.3776')
    expect(url.searchParams.get('z')).toBe('22')
    expect(url.searchParams.get('t')).toBe('k')
    expect(url.searchParams.get('output')).toBe('embed')
    expect(url.searchParams.get('q')).toBeNull()
  })

  it('rejects invalid coordinates, scale, and zoom', () => {
    expect(() =>
      buildGoogleMapsSatelliteEmbedUrl({ latitude: 91, longitude: 0 }),
    ).toThrow(RangeError)
    expect(() =>
      coursePointToGeo(
        { x: 0, y: 0 },
        { ...site, metersPerUnit: { x: 0, y: 1 } },
      ),
    ).toThrow(RangeError)
    expect(() => buildGoogleMapsSatelliteEmbedUrl(site.center, 23)).toThrow(
      RangeError,
    )
  })
})
