import { afterEach, describe, expect, it, vi } from 'vitest'
import { createBackendFlightAdapter } from '../data/backend-flight-adapter'

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  close = vi.fn()

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this)
  }
}

afterEach(() => {
  vi.restoreAllMocks()
  FakeWebSocket.instances = []
})

describe('backend flight adapter', () => {
  it('loads snapshots and posts commands to the FastAPI backend', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ link: 'connected' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ commandId: 'c1', status: 'accepted' }), { status: 200 })))
    const adapter = createBackendFlightAdapter('http://127.0.0.1:8000')

    await expect(adapter.getSnapshot()).resolves.toEqual({ link: 'connected' })
    await expect(adapter.sendCommand({ commandId: 'c1', type: 'arm' })).resolves.toEqual({
      commandId: 'c1',
      status: 'accepted',
    })
    expect(fetch).toHaveBeenNthCalledWith(2, 'http://127.0.0.1:8000/api/commands', expect.objectContaining({
      method: 'POST',
    }))
  })

  it('dispatches websocket events and closes the subscription', () => {
    vi.stubGlobal('WebSocket', FakeWebSocket)
    const adapter = createBackendFlightAdapter('http://127.0.0.1:8000')
    const listener = vi.fn()
    const unsubscribe = adapter.subscribe(listener)
    const socket = FakeWebSocket.instances[0]
    expect(socket.url).toBe("ws://127.0.0.1:8000/ws/flight")

    socket.onmessage?.({ data: '{"type":"link","state":"connected"}' } as MessageEvent<string>)
    unsubscribe()
    expect(listener).toHaveBeenCalledWith({ type: 'link', state: 'connected' })
    expect(socket.close).toHaveBeenCalledOnce()
  })

  it('uses secure websocket protocol for secure backend URLs', () => {
    vi.stubGlobal('WebSocket', FakeWebSocket)
    createBackendFlightAdapter('https://example.test/')
      .subscribe(() => {})
    expect(FakeWebSocket.instances[0].url).toBe('wss://example.test/ws/flight')
  })
})
