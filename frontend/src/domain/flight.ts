export type LinkState = 'connected' | 'stale' | 'disconnected'
export type FlightMode = 'MANUAL' | 'AUTO' | 'HOLD' | 'ELS'
export type CameraId = 'front' | 'down'
export type VisionClass =
  | 'person'
  | 'aruco'
  | 'gate'
  | 'drop_zone'
  | 'line'
  | 'landing_pad'
export type PayloadState = 'secured' | 'armed' | 'released' | 'unknown'
export type ElsState = 'standby' | 'countdown' | 'active'
export type MissionStatus = 'ready' | 'active' | 'passed' | 'failed' | 'retry'
export type RetryCheckpoint = 'START' | 'WP1' | 'WP2' | 'WP4'
export type CommandType =
  | 'arm'
  | 'enable_autonomy'
  | 'pause_mission'
  | 'retry'
  | 'emergency_land'

export type GeoPoint = { latitude: number; longitude: number }
export type NormalizedPoint = { x: number; y: number }
export type NormalizedBox = NormalizedPoint & {
  width: number
  height: number
}

export type TelemetryEvent = {
  type: 'telemetry'
  seq: number
  timestampMs: number
  armed: boolean
  mode: FlightMode
  batteryPercent: number
  voltage: number
  latitude: number | null
  longitude: number | null
  gpsFix: number
  gpsSatellites: number
  hdop: number | null
  localXM: number | null
  localYM: number | null
  altitudeM: number
  rangefinderM: number | null
  groundSpeedMps: number
  headingDeg: number
  rollDeg: number
  pitchDeg: number
  yawDeg: number
  collisionClearanceM: number | null
}

export type VisionEvent = {
  type: 'vision'
  seq: number
  timestampMs: number
  id: string
  frameId: number
  camera: CameraId
  className: VisionClass
  confidence: number
  box?: NormalizedBox
  path?: NormalizedPoint[]
  markerId?: number
}

export type MissionEvent = {
  type: 'mission'
  seq: number
  timestampMs: number
  phase: 1 | 2 | 3 | 4 | 5
  phaseName: string
  waypointLabel: string
  status: MissionStatus
  elapsedSeconds: number
  score: number
  retryCheckpoint: RetryCheckpoint
  autonomyReady: boolean
}

export type PayloadEvent = {
  type: 'payload'
  seq: number
  timestampMs: number
  state: PayloadState
}

export type SafetyEvent = {
  type: 'safety'
  seq: number
  timestampMs: number
  linkLostSeconds: number
  elsState: ElsState
  personWarning: boolean
  obstacleWarning: boolean
}

export type MapEvent = {
  type: 'map'
  seq: number
  timestampMs: number
  baseAvailable: boolean
}

export type CameraEvent = {
  type: 'camera'
  seq: number
  timestampMs: number
  id: CameraId
  connected: boolean
  latencyMs: number
  fps: number
}

export type FlightEvent =
  | TelemetryEvent
  | VisionEvent
  | MissionEvent
  | PayloadEvent
  | SafetyEvent
  | MapEvent
  | CameraEvent
  | { type: 'link'; seq: number; timestampMs: number; state: LinkState }
  | { type: 'trim_vision'; seq: number; timestampMs: number }

export type VisionTarget = Omit<VisionEvent, 'type' | 'seq'>
export type MissionState = Omit<
  MissionEvent,
  'type' | 'seq' | 'timestampMs'
>
export type SafetyState = Omit<
  SafetyEvent,
  'type' | 'seq' | 'timestampMs'
> & { personAcknowledged: boolean }

export type CommandRequest = { commandId: string; type: CommandType }
export type CommandResult = {
  commandId: string
  status: 'accepted' | 'rejected' | 'unknown'
  reason?: string
}
