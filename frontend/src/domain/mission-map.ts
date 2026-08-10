import type { GeoPoint } from './flight'

export const EARTH_RADIUS_METERS = 6_371_008.8

export type GeoCoordinate = GeoPoint
export type CoursePoint = { x: number; y: number }
export type OverlayPoint = CoursePoint

export type MissionSite = {
  name: string
  center: GeoCoordinate
  courseReference: CoursePoint
  metersPerUnit: CoursePoint
  courseUpBearingDeg: number
}

export type OverlayCalibration = {
  courseAnchor: CoursePoint
  mapAnchor: OverlayPoint
  scaleX: number
  scaleY: number
  rotationDeg: number
}

function toRadians(value: number) {
  return (value * Math.PI) / 180
}

function toDegrees(value: number) {
  return (value * 180) / Math.PI
}

function normalizeDegrees(value: number) {
  return ((value % 360) + 360) % 360
}

function validateCoordinate(point: GeoCoordinate) {
  if (
    !Number.isFinite(point.latitude) ||
    !Number.isFinite(point.longitude) ||
    point.latitude < -90 ||
    point.latitude > 90 ||
    point.longitude < -180 ||
    point.longitude > 180
  ) {
    throw new RangeError('Map point must be a valid GPS coordinate.')
  }
}

function validatePoint(point: CoursePoint) {
  if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) {
    throw new RangeError('Map point must contain finite x/y values.')
  }
}

function validateSite(site: MissionSite) {
  validateCoordinate(site.center)
  validatePoint(site.courseReference)
  if (
    !Number.isFinite(site.metersPerUnit.x) ||
    !Number.isFinite(site.metersPerUnit.y) ||
    site.metersPerUnit.x <= 0 ||
    site.metersPerUnit.y <= 0 ||
    !Number.isFinite(site.courseUpBearingDeg)
  ) {
    throw new RangeError('Mission-site scale must be finite and positive.')
  }
}

function validateCalibration(calibration: OverlayCalibration) {
  validatePoint(calibration.courseAnchor)
  validatePoint(calibration.mapAnchor)
  if (
    !Number.isFinite(calibration.scaleX) ||
    calibration.scaleX === 0 ||
    !Number.isFinite(calibration.scaleY) ||
    calibration.scaleY === 0 ||
    !Number.isFinite(calibration.rotationDeg)
  ) {
    throw new RangeError('Overlay scales must be finite and non-zero.')
  }
}

function rotate(point: CoursePoint, degrees: number): CoursePoint {
  const radians = toRadians(degrees)
  const cosine = Math.cos(radians)
  const sine = Math.sin(radians)
  return {
    x: point.x * cosine - point.y * sine,
    y: point.x * sine + point.y * cosine,
  }
}

export function coursePointToGeo(
  point: CoursePoint,
  site: MissionSite,
): GeoCoordinate {
  validatePoint(point)
  validateSite(site)
  const localEast =
    (point.x - site.courseReference.x) * site.metersPerUnit.x
  const localNorth =
    (site.courseReference.y - point.y) * site.metersPerUnit.y
  const bearing = toRadians(site.courseUpBearingDeg)
  const east = localEast * Math.cos(bearing) + localNorth * Math.sin(bearing)
  const north = -localEast * Math.sin(bearing) + localNorth * Math.cos(bearing)
  const centerLatitude = toRadians(site.center.latitude)
  return {
    latitude: site.center.latitude + toDegrees(north / EARTH_RADIUS_METERS),
    longitude:
      site.center.longitude +
      toDegrees(east / (EARTH_RADIUS_METERS * Math.cos(centerLatitude))),
  }
}

export function geoPointToCourse(
  point: GeoCoordinate,
  site: MissionSite,
): CoursePoint {
  validateCoordinate(point)
  validateSite(site)
  const centerLatitude = toRadians(site.center.latitude)
  const east =
    toRadians(point.longitude - site.center.longitude) *
    EARTH_RADIUS_METERS *
    Math.cos(centerLatitude)
  const north =
    toRadians(point.latitude - site.center.latitude) * EARTH_RADIUS_METERS
  const bearing = toRadians(site.courseUpBearingDeg)
  const localEast = east * Math.cos(bearing) - north * Math.sin(bearing)
  const localNorth = east * Math.sin(bearing) + north * Math.cos(bearing)
  return {
    x: site.courseReference.x + localEast / site.metersPerUnit.x,
    y: site.courseReference.y - localNorth / site.metersPerUnit.y,
  }
}

export function coursePointToOverlay(
  point: CoursePoint,
  calibration: OverlayCalibration,
): OverlayPoint {
  validatePoint(point)
  validateCalibration(calibration)
  const rotated = rotate(
    {
      x: (point.x - calibration.courseAnchor.x) * calibration.scaleX,
      y: (point.y - calibration.courseAnchor.y) * calibration.scaleY,
    },
    calibration.rotationDeg,
  )
  return {
    x: calibration.mapAnchor.x + rotated.x,
    y: calibration.mapAnchor.y + rotated.y,
  }
}

export function courseHeadingToOverlay(
  headingDeg: number,
  calibration: OverlayCalibration,
) {
  if (!Number.isFinite(headingDeg)) {
    throw new RangeError('Overlay heading must be finite.')
  }
  validateCalibration(calibration)
  const radians = toRadians(headingDeg)
  const rotated = rotate(
    {
      x: Math.sin(radians) * calibration.scaleX,
      y: -Math.cos(radians) * calibration.scaleY,
    },
    calibration.rotationDeg,
  )
  return normalizeDegrees(toDegrees(Math.atan2(rotated.x, -rotated.y)))
}

export function buildGoogleMapsSatelliteEmbedUrl(
  center: GeoCoordinate,
  zoom = 22,
) {
  validateCoordinate(center)
  if (!Number.isInteger(zoom) || zoom < 1 || zoom > 22) {
    throw new RangeError('Google Maps zoom must be an integer from 1 to 22.')
  }
  const url = new URL('https://maps.google.com/maps')
  url.searchParams.set('ll', `${center.latitude},${center.longitude}`)
  url.searchParams.set('z', String(zoom))
  url.searchParams.set('t', 'k')
  url.searchParams.set('output', 'embed')
  return url.toString()
}
