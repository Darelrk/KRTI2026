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
  type MissionSite,
  type OverlayCalibration,
} from '../domain/mission-map'

type Props = {
  telemetry: TelemetryEvent | null
  mission: FlightState['mission']
  site?: MissionSite
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

function localPosition(telemetry: TelemetryEvent | null) {
  if (telemetry?.localXM === null || telemetry?.localYM === null || !telemetry) {
    return null
  }
  return {
    x: 50 + telemetry.localXM / 0.8,
    y: 50 - telemetry.localYM / 0.6,
  }
}

function formatCoordinate(value: number, positive: string, negative: string) {
  return `${Math.abs(value).toFixed(6)}° ${value >= 0 ? positive : negative}`
}


export function NavigationMap({
  telemetry,
  mission,
  site,
  calibration,
  baseMapAvailable,
}: Props) {
  const livePosition = telemetryPosition(telemetry)
  const [mapCenter, setMapCenter] = useState(() => site?.center ?? livePosition ?? null)
  const [refreshKey, setRefreshKey] = useState(0)
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
            src={buildGoogleMapsSatelliteEmbedUrl(mapCenter!, 16)}
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
        {currentPoint && telemetry && (
          <svg
            className="navigation-map__overlay"
            viewBox="0 0 100 100"
            role="img"
            aria-label="VTOL drone position"
          >
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
          </svg>
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
        ) : (
          <span>POSITION UNAVAILABLE</span>
        )}
      </footer>
    </section>
  )
}
