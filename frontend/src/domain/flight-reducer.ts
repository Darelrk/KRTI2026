import type {
  CameraId,
  FlightEvent,
  GeoPoint,
  LinkState,
  MissionState,
  PayloadState,
  SafetyState,
  TelemetryEvent,
  VisionTarget,
} from './flight'

export type FlightState = {
  telemetry: TelemetryEvent | null
  track: GeoPoint[]
  link: LinkState
  camera: {
    id: CameraId
    connected: boolean
    latencyMs: number
    fps: number
  }
  map: { baseAvailable: boolean }
  mission: MissionState
  payload: PayloadState
  safety: SafetyState
  visionTargets: VisionTarget[]
  lastEventAt: number
}

export type FlightAction =
  | FlightEvent
  | { type: 'ack_person_warning' }

export const initialFlightState: FlightState = {
  telemetry: null,
  track: [],
  link: 'disconnected',
  camera: {
    id: 'front',
    connected: false,
    latencyMs: 0,
    fps: 0,
  },
  map: { baseAvailable: true },
  mission: {
    phase: 1,
    phaseName: 'Manual navigation and transition',
    waypointLabel: 'START',
    status: 'ready',
    elapsedSeconds: 0,
    score: 0,
    retryCheckpoint: 'START',
    autonomyReady: false,
  },
  payload: 'unknown',
  safety: {
    linkLostSeconds: 0,
    elsState: 'standby',
    personWarning: false,
    personAcknowledged: false,
    obstacleWarning: false,
  },
  visionTargets: [],
  lastEventAt: 0,
}

export function reduceFlightEvent(
  state: FlightState,
  event: FlightAction,
): FlightState {
  if (event.type === 'ack_person_warning') {
    return {
      ...state,
      safety: { ...state.safety, personAcknowledged: true },
    }
  }

  if (event.type === 'telemetry') {
    const hasGps = event.latitude !== null && event.longitude !== null
    const track = hasGps
      ? [
          ...state.track,
          { latitude: event.latitude!, longitude: event.longitude! },
        ].slice(-121)
      : state.track
    return { ...state, telemetry: event, track, lastEventAt: event.timestampMs }
  }

  if (event.type === 'link') {
    return { ...state, link: event.state, lastEventAt: event.timestampMs }
  }

  if (event.type === 'camera') {
    return {
      ...state,
      camera: {
        id: event.id,
        connected: event.connected,
        latencyMs: event.latencyMs,
        fps: event.fps,
      },
      lastEventAt: event.timestampMs,
    }
  }

  if (event.type === 'map') {
    return {
      ...state,
      map: { baseAvailable: event.baseAvailable },
      lastEventAt: event.timestampMs,
    }
  }

  if (event.type === 'mission') {
    const {
      type: _type,
      seq: _seq,
      timestampMs,
      ...mission
    } = event
    return { ...state, mission, lastEventAt: timestampMs }
  }

  if (event.type === 'payload') {
    return {
      ...state,
      payload: event.state,
      lastEventAt: event.timestampMs,
    }
  }

  if (event.type === 'safety') {
    const personAcknowledged =
      event.personWarning && state.safety.personWarning
        ? state.safety.personAcknowledged
        : false
    return {
      ...state,
      safety: {
        linkLostSeconds: event.linkLostSeconds,
        elsState: event.elsState,
        personWarning: event.personWarning,
        personAcknowledged,
        obstacleWarning: event.obstacleWarning,
      },
      lastEventAt: event.timestampMs,
    }
  }

  if (event.type === 'vision') {
    const { type: _type, seq: _seq, ...target } = event
    return {
      ...state,
      visionTargets: [target, ...state.visionTargets].slice(0, 20),
      lastEventAt: event.timestampMs,
    }
  }

  return {
    ...state,
    visionTargets: state.visionTargets.slice(0, 20),
    lastEventAt: event.timestampMs,
  }
}
