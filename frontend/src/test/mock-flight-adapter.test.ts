import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMockFlightAdapter } from '../data/mock-flight-adapter'
import type { FlightEvent } from '../domain/flight'

afterEach(() => vi.useRealTimers())

function collectScenario(scenario: Parameters<typeof createMockFlightAdapter>[0]) {
  const events: FlightEvent[] = []
  const unsubscribe = createMockFlightAdapter(scenario).subscribe((event) =>
    events.push(event),
  )
  return { events, unsubscribe }
}

describe('mock VTOL flight adapter', () => {
  it('publishes complete initial VTOL state and periodic telemetry', () => {
    vi.useFakeTimers()
    const { events, unsubscribe } = collectScenario('normal')
    expect(events.map((event) => event.type)).toEqual([
      'link',
      'camera',
      'map',
      'mission',
      'payload',
      'safety',
      'telemetry',
    ])
    const telemetry = events.find((event) => event.type === 'telemetry')
    expect(telemetry).toMatchObject({
      mode: 'MANUAL',
      latitude: 3.5633609133111217,
      longitude: 98.67340287653748,
      localXM: 12.5,
      localYM: 8.25,
      rangefinderM: 5.9,
      rollDeg: 1.2,
      pitchDeg: -0.7,
      yawDeg: 91,
    })
    vi.advanceTimersByTime(1_000)
    expect(
      events.filter((event) => event.type === 'telemetry').length,
    ).toBeGreaterThan(1)
    unsubscribe()
    const count = events.length
    vi.advanceTimersByTime(1_000)
    expect(events).toHaveLength(count)
  })

  it('emits a person overlay and passive safety warning', () => {
    vi.useFakeTimers()
    const { events, unsubscribe } = collectScenario('person-warning')
    expect(events.find((event) => event.type === 'vision')).toMatchObject({
      className: 'person',
      camera: 'front',
      box: { x: 0.637, y: 0.41, width: 0.058, height: 0.156 },
    })
    expect(events.find((event) => event.type === 'safety')).toMatchObject({
      personWarning: true,
    })
    unsubscribe()
  })

  it('keeps local position when GPS has no fix', () => {
    vi.useFakeTimers()
    const { events, unsubscribe } = collectScenario('gps-no-fix')
    expect(events.find((event) => event.type === 'telemetry')).toMatchObject({
      latitude: null,
      longitude: null,
      gpsFix: 0,
      gpsSatellites: 0,
      localXM: 12.5,
      localYM: 8.25,
    })
    unsubscribe()
  })

  it('reports backend-owned ELS and payload states', () => {
    vi.useFakeTimers()
    const els = collectScenario('els-active')
    expect(els.events.find((event) => event.type === 'safety')).toMatchObject({
      linkLostSeconds: 16,
      elsState: 'active',
    })
    expect(els.events.find((event) => event.type === 'telemetry')).toMatchObject({
      mode: 'ELS',
    })
    els.unsubscribe()

    const payload = collectScenario('payload-released')
    expect(payload.events.find((event) => event.type === 'payload')).toMatchObject({
      state: 'released',
    })
    payload.unsubscribe()
  })

  it('reports satellite base-map availability through the event contract', () => {
    vi.useFakeTimers()
    const { events, unsubscribe } = collectScenario('map-unavailable')
    expect(events.find((event) => event.type === 'map')).toMatchObject({
      baseAvailable: false,
    })
    unsubscribe()
  })

  it('accepts autonomy only at a ready WP1 transition', async () => {
    vi.useFakeTimers()
    const blocked = createMockFlightAdapter('normal').sendCommand({
      commandId: 'blocked',
      type: 'enable_autonomy',
    })
    const accepted = createMockFlightAdapter('auto-transition').sendCommand({
      commandId: 'accepted',
      type: 'enable_autonomy',
    })
    await vi.advanceTimersByTimeAsync(350)
    await expect(blocked).resolves.toMatchObject({
      status: 'rejected',
      reason: 'Autonomy is not ready at WP1',
    })
    await expect(accepted).resolves.toMatchObject({ status: 'accepted' })
  })

  it('waits for acknowledgment and preserves rejection reasons', async () => {
    vi.useFakeTimers()
    let settled = false
    const pending = createMockFlightAdapter('command-rejected')
      .sendCommand({ commandId: 'command-1', type: 'arm' })
      .finally(() => {
        settled = true
      })
    await vi.advanceTimersByTimeAsync(349)
    expect(settled).toBe(false)
    await vi.advanceTimersByTimeAsync(1)
    await expect(pending).resolves.toEqual({
      commandId: 'command-1',
      status: 'rejected',
      reason: 'Pre-arm checks failed',
    })
  })
})
