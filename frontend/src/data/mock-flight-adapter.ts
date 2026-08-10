import type { FlightAdapter } from './flight-adapter'
import type {
  CommandRequest,
  FlightEvent,
  TelemetryEvent,
  VisionClass,
} from '../domain/flight'
import {
  initialFlightState,
  reduceFlightEvent,
} from '../domain/flight-reducer'

export type MockScenario =
  | 'normal'
  | 'auto-transition'
  | 'person-warning'
  | 'vision-targets'
  | 'payload-released'
  | 'retry'
  | 'low-battery'
  | 'gps-no-fix'
  | 'map-unavailable'
  | 'camera-lost'
  | 'els-active'
  | 'collision-warning'
  | 'command-rejected'

const scenarios: Record<MockScenario, true> = {
  normal: true,
  'auto-transition': true,
  'person-warning': true,
  'vision-targets': true,
  'payload-released': true,
  retry: true,
  'low-battery': true,
  'gps-no-fix': true,
  'map-unavailable': true,
  'camera-lost': true,
  'els-active': true,
  'collision-warning': true,
  'command-rejected': true,
}

function currentScenario(): MockScenario {
  if (typeof window === 'undefined' || !import.meta.env.DEV) return 'normal'
  const value = new URLSearchParams(window.location.search).get('scenario')
  return value && value in scenarios ? (value as MockScenario) : 'normal'
}

function telemetryFor(
  scenario: MockScenario,
  timestampMs: number,
  seq: number,
  tick = 0,
): TelemetryEvent {
  const noGps = scenario === 'gps-no-fix'
  return {
    type: 'telemetry',
    seq,
    timestampMs,
    armed: true,
    mode:
      scenario === 'els-active'
        ? 'ELS'
        : scenario === 'auto-transition'
          ? 'AUTO'
          : 'MANUAL',
    batteryPercent:
      scenario === 'low-battery'
        ? 18
        : Math.max(19, 72 - Math.floor(tick / 300)),
    voltage: scenario === 'low-battery' ? 13.7 : 15.9,
    latitude: noGps ? null : -7.7706 + tick / 1_000_000,
    longitude: noGps ? null : 110.3776 + tick / 1_000_000,
    gpsFix: noGps ? 0 : 3,
    gpsSatellites: noGps ? 0 : 12,
    hdop: noGps ? null : 0.8,
    localXM: 12.5 + tick / 50,
    localYM: 8.25 + tick / 100,
    altitudeM: 6.4,
    rangefinderM: 5.9,
    groundSpeedMps: 2.3,
    headingDeg: (91 + tick) % 360,
    rollDeg: 1.2,
    pitchDeg: -0.7,
    yawDeg: (91 + tick) % 360,
    collisionClearanceM: scenario === 'collision-warning' ? 0.45 : 3.8,
  }
}

function initialEvents(scenario: MockScenario, now: number): FlightEvent[] {
  let seq = 0
  const events: FlightEvent[] = [
    {
      type: 'link',
      seq: ++seq,
      timestampMs: now,
      state: scenario === 'els-active' ? 'disconnected' : 'connected',
    },
    {
      type: 'camera',
      seq: ++seq,
      timestampMs: now,
      id: 'front',
      connected: scenario !== 'camera-lost',
      latencyMs: 112,
      fps: 24,
    },
    {
      type: 'map',
      seq: ++seq,
      timestampMs: now,
      baseAvailable: scenario !== 'map-unavailable',
    },
    {
      type: 'mission',
      seq: ++seq,
      timestampMs: now,
      phase: scenario === 'retry' ? 3 : 1,
      phaseName:
        scenario === 'retry'
          ? 'Triple gate navigation'
          : 'Manual navigation and transition',
      waypointLabel: scenario === 'retry' ? 'WP2' : 'WP1',
      status:
        scenario === 'retry'
          ? 'retry'
          : scenario === 'auto-transition'
            ? 'passed'
            : 'active',
      elapsedSeconds: 125,
      score: scenario === 'auto-transition' ? 10 : 0,
      retryCheckpoint: scenario === 'retry' ? 'WP2' : 'START',
      autonomyReady: scenario === 'auto-transition',
    },
    {
      type: 'payload',
      seq: ++seq,
      timestampMs: now,
      state: scenario === 'payload-released' ? 'released' : 'secured',
    },
    {
      type: 'safety',
      seq: ++seq,
      timestampMs: now,
      linkLostSeconds: scenario === 'els-active' ? 16 : 0,
      elsState: scenario === 'els-active' ? 'active' : 'standby',
      personWarning: scenario === 'person-warning',
      obstacleWarning: scenario === 'collision-warning',
    },
    telemetryFor(scenario, now, ++seq),
  ]

  const publishVision = (
    className: VisionClass,
    geometry: Pick<FlightEvent & { type: 'vision' }, 'box' | 'path' | 'markerId'>,
    camera: 'front' | 'down' = 'front',
  ) => {
    events.push({
      type: 'vision',
      seq: ++seq,
      timestampMs: now,
      id: `${className}-${seq}`,
      frameId: 1,
      camera,
      className,
      confidence: className === 'person' ? 0.91 : 0.96,
      ...geometry,
    })
  }

  if (scenario === 'person-warning') {
    publishVision('person', {
      box: { x: 0.637, y: 0.41, width: 0.058, height: 0.156 },
    })
  }
  if (scenario === 'vision-targets') {
    publishVision('aruco', {
      box: { x: 0.45, y: 0.55, width: 0.08, height: 0.12 },
      markerId: 17,
    }, 'down')
    publishVision('gate', {
      box: { x: 0.2, y: 0.18, width: 0.58, height: 0.62 },
    })
    publishVision('drop_zone', {
      box: { x: 0.38, y: 0.62, width: 0.24, height: 0.2 },
    }, 'down')
    publishVision('line', {
      path: [{ x: 0.1, y: 0.8 }, { x: 0.5, y: 0.5 }, { x: 0.9, y: 0.2 }],
    }, 'down')
    publishVision('landing_pad', {
      box: { x: 0.25, y: 0.5, width: 0.5, height: 0.4 },
    }, 'down')
  }
  return events
}

export function createMockFlightAdapter(
  scenario: MockScenario,
): FlightAdapter {
  return {
    async getSnapshot() {
      return initialEvents(scenario, Date.now()).reduce(
        reduceFlightEvent,
        initialFlightState,
      )
    },

    subscribe(listener) {
      let tick = 0
      let seq = 100
      initialEvents(scenario, Date.now()).forEach(listener)
      const timer = window.setInterval(() => {
        tick += 1
        if (tick % 5 === 0) {
          listener(telemetryFor(scenario, Date.now(), ++seq, tick))
        }
      }, 200)
      return () => window.clearInterval(timer)
    },

    async sendCommand(command: CommandRequest) {
      const { promise, resolve } = Promise.withResolvers<void>()
      window.setTimeout(resolve, 350)
      await promise
      if (scenario === 'command-rejected') {
        return {
          commandId: command.commandId,
          status: 'rejected',
          reason: 'Pre-arm checks failed',
        }
      }
      if (
        command.type === 'enable_autonomy' &&
        scenario !== 'auto-transition'
      ) {
        return {
          commandId: command.commandId,
          status: 'rejected',
          reason: 'Autonomy is not ready at WP1',
        }
      }
      return { commandId: command.commandId, status: 'accepted' }
    },
  }
}

export const mockFlightAdapter = createMockFlightAdapter(currentScenario())
