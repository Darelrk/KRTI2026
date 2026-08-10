import type { FlightAdapter } from './flight-adapter'
import type { CommandRequest, CommandResult, FlightEvent } from '../domain/flight'
import type { FlightState } from '../domain/flight-reducer'

export class HttpFlightAdapter implements FlightAdapter {
  private readonly apiUrl: string
  private readonly websocketUrl: string

  constructor(baseUrl: string) {
    const url = new URL(baseUrl)
    url.pathname = url.pathname.replace(/\/$/, '')
    url.search = ''
    url.hash = ''
    this.apiUrl = url.toString().replace(/\/$/, '')
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    this.websocketUrl = url.toString().replace(/\/$/, '')
  }

  async getSnapshot(): Promise<FlightState> {
    const response = await fetch(`${this.apiUrl}/api/snapshot`)
    return this.readResponse<FlightState>(response)
  }

  subscribe(listener: (event: FlightEvent) => void): () => void {
    const socket = new WebSocket(`${this.websocketUrl}/ws/flight`)
    socket.onmessage = (event) => listener(JSON.parse(event.data) as FlightEvent)
    return () => socket.close()
  }

  async sendCommand(command: CommandRequest): Promise<CommandResult> {
    const response = await fetch(`${this.apiUrl}/api/commands`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(command),
    })
    return this.readResponse<CommandResult>(response)
  }

  private async readResponse<T>(response: Response): Promise<T> {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string; reason?: string }
      | T
      | null
    if (!response.ok) {
      const error = body && typeof body === 'object' && ('detail' in body || 'reason' in body)
        ? ('detail' in body ? body.detail : body.reason)
        : undefined
      throw new Error(error || `backend request failed: ${response.status}`)
    }
    return body as T
  }
}

export function createBackendFlightAdapter(
  baseUrl = import.meta.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000',
): FlightAdapter {
  return new HttpFlightAdapter(baseUrl)
}

export const backendFlightAdapter = import.meta.env.VITE_BACKEND_URL
  ? createBackendFlightAdapter(import.meta.env.VITE_BACKEND_URL)
  : null
