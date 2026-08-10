import { Button } from '@carbon/react'
import { Renew } from '@carbon/icons-react'
import { useState } from 'react'
import type { TelemetryEvent } from '../domain/flight'
import type { FlightState } from '../domain/flight-reducer'
import {
  buildGoogleMapsSatelliteEmbedUrl,
  courseHeadingToOverlay,
  coursePointToOverlay,
  geoPointToCourse,
} from '../domain/mission-map'
import type {
  CoursePoint,
  MissionSite,
  OverlayCalibration,
} from '../domain/mission-map'

export type RouteMarker = {
  id: string
  kind: 'start' | 'waypoint' | 'gate' | 'drop_zone' | 'landing_pad'
  point: CoursePoint
}

type Props = {
  telemetry: TelemetryEvent | null
  track: FlightState['track']
  mission: FlightState['mission']
  site?: MissionSite
  route: RouteMarker[]
  calibration: OverlayCalibration
  baseMapAvailable: boolean
}

function telemetryPosition(telemetry: TelemetryEvent | null) {
  return telemetry !== null &&
    telemetry.latitude !== null &&
    telemetry.longitude !== null
    ? { latitude: telemetry.latitude, longitude: telemetry.longitude }
    : null
}

function localPosition(telemetry: TelemetryEvent | null): CoursePoint | null {
  if (telemetry?.localXM === null || telemetry?.localYM === null || !telemetry) {
    return null
  }
  return {
    x: 50 + telemetry.localXM / 0.8,
    y: 50 - telemetry.localYM / 0.6,
  }
}

function formatPoint(point: CoursePoint) {
  return `${point.x},${point.y}`
}

function formatCoordinate(value: number, positive: string, negative: string) {
  return `${Math.abs(value).toFixed(6)}° ${value >= 0 ? positive : negative}`
}

export function NavigationMap({
  telemetry,
  track,
  mission,
  site,
  route,
  calibration,
  baseMapAvailable,
}: Props) {
  const livePosition = telemetryPosition(telemetry) ?? track.at(-1) ?? null
  const [mapCenter, setMapCenter] = useState(() => livePosition ?? site?.center ?? null)
  const [refreshKey, setRefreshKey] = useState(0)
  const routePoints = route.map(({ point }) =>
    coursePointToOverlay(point, calibration),
  )
  const trackPoints = site
    ? track.map((point) =>
        coursePointToOverlay(geoPointToCourse(point, site), calibration),
      )
    : []
  const currentPoint = site && livePosition
    ? coursePointToOverlay(geoPointToCourse(livePosition, site), calibration)
    : localPosition(telemetry)
      ? coursePointToOverlay(localPosition(telemetry)!, calibration)
      : null
  const overlayHeading = telemetry
    ? courseHeadingToOverlay(telemetry.headingDeg, calibration)
    : 0
  const showSatellite = baseMapAvailable && site !== undefined && mapCenter !== null

  return (
    <section className="navigation-map" aria-labelledby="navigation-map-title">
      <header className="navigation-map__header">
        <div>
          <span>GPS / local route</span>
          <h2 id="navigation-map-title">VTOL mission map</h2>
        </div>
        <Button
          hasIconOnly
          iconDescription="Refresh map"
          kind="ghost"
          onClick={() => {
            if (livePosition && site) setMapCenter(livePosition)
            setRefreshKey((value) => value + 1)
          }}
          renderIcon={Renew}
          size="sm"
        />
      </header>
      <div className="navigation-map__canvas">
        <div className="navigation-map__grid" aria-hidden="true" />
        {showSatellite ? (
          <iframe
            key={refreshKey}
            className="navigation-map__base"
            src={buildGoogleMapsSatelliteEmbedUrl(mapCenter!)}
            title="VTOL satellite base map"
            tabIndex={-1}
          />
        ) : (
          <strong className="navigation-map__unavailable">
            SATELLITE MAP UNAVAILABLE
          </strong>
        )}
        <div className="navigation-map__wash" aria-hidden="true" />
        <div className="navigation-map__north" aria-label="North up">
          N ↑
        </div>
        <svg
          className="navigation-map__overlay"
          viewBox="0 0 100 100"
          role="img"
          aria-label="VTOL map overlay"
        >
          <polyline
            aria-label="VTOL mission route"
            className="navigation-map__route"
            points={routePoints.map(formatPoint).join(' ')}
            fill="none"
          />
          {trackPoints.length > 1 && (
            <polyline
              aria-label="VTOL travelled track"
              className="navigation-map__track"
              points={trackPoints.map(formatPoint).join(' ')}
              fill="none"
            />
          )}
          {route.map((marker, index) => {
            const point = routePoints[index]!
            return (
              <g
                key={marker.id}
                aria-label={`${marker.kind} ${marker.id}`}
                className={`navigation-map__marker navigation-map__marker--${marker.kind}`}
                transform={`translate(${point.x} ${point.y})`}
              >
                <circle r="1.8" />
                <text x="2.5" y="1">
                  {marker.id.toUpperCase()}
                </text>
              </g>
            )
          })}
          {currentPoint && telemetry && (
            <g
              aria-label="VTOL position marker"
              className="navigation-map__vehicle"
              data-course-heading={telemetry.headingDeg}
              data-overlay-heading={overlayHeading}
              transform={`translate(${currentPoint.x} ${currentPoint.y}) rotate(${overlayHeading})`}
            >
              <circle r="3.4" />
              <path d="M 0 -4.2 L 2.5 3.2 L 0 1.8 L -2.5 3.2 Z" />
            </g>
          )}
        </svg>
        {!currentPoint && (
          <div className="navigation-map__empty">WAITING FOR GPS FIX</div>
        )}
      </div>
      <footer className="navigation-map__readout">
        <span>
          MISSION {mission.phase} · {mission.waypointLabel}
        </span>
        {site && livePosition ? (
          <span className="navigation-map__coordinate">
            {formatCoordinate(livePosition.latitude, 'N', 'S')} ·{' '}
            {formatCoordinate(livePosition.longitude, 'E', 'W')}
          </span>
        ) : currentPoint ? (
          <span>LOCAL POSITION ACTIVE</span>
        ) : (
          <span>POSITION UNAVAILABLE</span>
        )}
      </footer>
    </section>
  )
}
