import { describe, expect, it } from 'vitest'
import type {
  MissionEvent,
  PayloadEvent,
  SafetyEvent,
  TelemetryEvent,
  VisionEvent,
} from '../domain/flight'
import { initialFlightState, reduceFlightEvent } from '../domain/flight-reducer'

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

const mission: MissionEvent = {
  type: 'mission',
  seq: 2,
  timestampMs: 2_000,
  phase: 2,
  phaseName: 'Autonomous medical delivery',
  waypointLabel: 'WP2',
  status: 'active',
  elapsedSeconds: 125,
  score: 15,
  retryCheckpoint: 'WP1',
  autonomyReady: true,
}

describe('flight reducer', () => {
  it('stores complete telemetry and appends a valid GPS track point', () => {
    const next = reduceFlightEvent(initialFlightState, telemetry)
    expect(next.telemetry).toEqual(telemetry)
    expect(next.track).toEqual([
      { latitude: -7.7706, longitude: 110.3776 },
    ])
    expect(next.lastEventAt).toBe(1_000)
  })

  it('does not invent a GPS track point when position has no fix', () => {
    const next = reduceFlightEvent(initialFlightState, {
      ...telemetry,
      latitude: null,
      longitude: null,
    })
    expect(next.track).toEqual([])
  })

  it('caps the GPS track at 121 newest points', () => {
    const next = Array.from({ length: 130 }, (_, index) => index).reduce(
      (state, index) =>
        reduceFlightEvent(state, {
          ...telemetry,
          seq: index,
          timestampMs: index,
          latitude: -7.77 + index / 100_000,
        }),
      initialFlightState,
    )
    expect(next.track).toHaveLength(121)
    expect(next.track[0]?.latitude).toBeCloseTo(-7.76991)
  })

  it('stores mission, payload, and safety snapshots atomically', () => {
    const payload: PayloadEvent = {
      type: 'payload',
      seq: 3,
      timestampMs: 3_000,
      state: 'released',
    }
    const safety: SafetyEvent = {
      type: 'safety',
      seq: 4,
      timestampMs: 4_000,
      linkLostSeconds: 16,
      elsState: 'active',
      personWarning: true,
      obstacleWarning: false,
    }
    const withMission = reduceFlightEvent(initialFlightState, mission)
    const withPayload = reduceFlightEvent(withMission, payload)
    const next = reduceFlightEvent(withPayload, safety)

    expect(next.mission).toMatchObject({
      phase: 2,
      score: 15,
      retryCheckpoint: 'WP1',
    })
    expect(next.payload).toBe('released')
    expect(next.safety).toMatchObject({
      linkLostSeconds: 16,
      elsState: 'active',
      personWarning: true,
      personAcknowledged: false,
    })
  })

  it('acknowledges a person warning without clearing backend warning state', () => {
    const warned = reduceFlightEvent(initialFlightState, {
      type: 'safety',
      seq: 4,
      timestampMs: 4_000,
      linkLostSeconds: 0,
      elsState: 'standby',
      personWarning: true,
      obstacleWarning: false,
    })
    const next = reduceFlightEvent(warned, { type: 'ack_person_warning' })
    expect(next.safety.personWarning).toBe(true)
    expect(next.safety.personAcknowledged).toBe(true)
  })

  it('stores both box and path vision geometry and trims to 20 targets', () => {
    const events: VisionEvent[] = Array.from({ length: 25 }, (_, index) => ({
      type: 'vision',
      seq: index,
      timestampMs: index,
      id: `target-${index}`,
      frameId: 12,
      camera: index % 2 === 0 ? 'front' : 'down',
      className: index === 0 ? 'line' : 'gate',
      confidence: 0.9,
      ...(index === 0
        ? { path: [{ x: 0.1, y: 0.8 }, { x: 0.9, y: 0.2 }] }
        : { box: { x: 0.2, y: 0.2, width: 0.1, height: 0.2 } }),
    }))
    const populated = events.reduce(reduceFlightEvent, initialFlightState)
    const next = reduceFlightEvent(populated, {
      type: 'trim_vision',
      seq: 30,
      timestampMs: 30,
    })
    expect(next.visionTargets).toHaveLength(20)
    expect(next.visionTargets[0]?.id).toBe('target-24')
  })

  it('updates base map availability independently', () => {
    const next = reduceFlightEvent(initialFlightState, {
      type: 'map',
      seq: 5,
      timestampMs: 5_000,
      baseAvailable: false,
    })
    expect(next.map.baseAvailable).toBe(false)
  })
})
