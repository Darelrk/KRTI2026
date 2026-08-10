import type {
  CommandRequest,
  CommandResult,
  FlightEvent,
} from '../domain/flight'
import type { FlightState } from '../domain/flight-reducer'

export interface FlightAdapter {
  getSnapshot(): Promise<FlightState>
  subscribe(listener: (event: FlightEvent) => void): () => void
  sendCommand(command: CommandRequest): Promise<CommandResult>
}
