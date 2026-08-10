import { createFileRoute } from '@tanstack/react-router'
import { CommandRail } from '../components/CommandRail'
import { CriticalAlert } from '../components/CriticalAlert'
import { DashboardShell } from '../components/DashboardShell'
import { MissionProgress } from '../components/MissionProgress'
import { NavigationMap } from '../components/NavigationMap'
import { PayloadStatus } from '../components/PayloadStatus'
import { PositionTelemetry } from '../components/PositionTelemetry'
import { SafetyEventQueue } from '../components/SafetyEventQueue'
import { StatusRail } from '../components/StatusRail'
import { VideoViewport } from '../components/VideoViewport'
import type { RouteMarker } from '../components/NavigationMap'
import type { OverlayCalibration } from '../domain/mission-map'
import { useFlightSession } from '../hooks/use-flight-session'

const route: RouteMarker[] = [
  { id: 'start', kind: 'start', point: { x: 12, y: 82 } },
  { id: 'wp1', kind: 'waypoint', point: { x: 30, y: 60 } },
  { id: 'wp2', kind: 'waypoint', point: { x: 52, y: 34 } },
  { id: 'drop', kind: 'drop_zone', point: { x: 74, y: 48 } },
  { id: 'land', kind: 'landing_pad', point: { x: 86, y: 78 } },
]

const calibration: OverlayCalibration = {
  courseAnchor: { x: 50, y: 50 },
  mapAnchor: { x: 50, y: 50 },
  scaleX: 0.9,
  scaleY: 0.9,
  rotationDeg: 0,
}

export const Route = createFileRoute('/')({ component: MissionOperationsPage })

function MissionOperationsPage() {
  const { state, command, acknowledgePersonWarning } = useFlightSession()
  const commandDisabled =
    state.link !== 'connected' || command.isPending

  return (
    <DashboardShell
      alert={<CriticalAlert state={state} />}
      status={<StatusRail state={state} />}
      video={<VideoViewport state={state} />}
      sidebar={
        <aside className="mission-sidebar">
          <NavigationMap
            telemetry={state.telemetry}
            track={state.track}
            mission={state.mission}
            route={route}
            calibration={calibration}
            baseMapAvailable={false}
          />
          <PositionTelemetry telemetry={state.telemetry} />
          <PayloadStatus state={state.payload} />
          <SafetyEventQueue
            link={state.link}
            safety={state.safety}
            onAcknowledgePerson={acknowledgePersonWarning}
          />
          <MissionProgress mission={state.mission} />
        </aside>
      }
      commands={
        <CommandRail
          armed={state.telemetry?.armed ?? false}
          autonomyReady={state.mission.autonomyReady}
          disabled={commandDisabled}
          retryCheckpoint={state.mission.retryCheckpoint}
          onCommand={(type) =>
            command.mutate({ commandId: crypto.randomUUID(), type })
          }
          result={command.data}
        />
      }
    />
  )
}
