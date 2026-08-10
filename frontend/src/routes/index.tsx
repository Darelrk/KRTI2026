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
import type { MissionSite, OverlayCalibration } from '../domain/mission-map'
import { useFlightSession } from '../hooks/use-flight-session'


const soewondoSite: MissionSite = {
  name: 'Lanud Soewondo',
  center: { latitude: 3.5633609133111217, longitude: 98.67340287653748 },
  courseReference: { x: 50, y: 50 },
  metersPerUnit: { x: 0.8, y: 0.6 },
  courseUpBearingDeg: 46,
}

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
            mission={state.mission}
            site={soewondoSite}
            calibration={calibration}
            baseMapAvailable
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
