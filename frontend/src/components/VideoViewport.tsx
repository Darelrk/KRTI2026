import { useState } from 'react'
import type { FlightState } from '../domain/flight-reducer'
import { VisionOverlay } from './VisionOverlay'

export function VideoViewport({ state }: { state: FlightState }) {
  const [nightVision, setNightVision] = useState(false)
  return (
    <section
      className={`video-viewport${nightVision ? ' video-viewport--nightvision' : ''}`}
      aria-label="Live camera"
    >
      <div className="video-viewport__controls">
        <div className="video-viewport__metrics">
          {state.camera.id.toUpperCase()} · {state.camera.fps} FPS /{' '}
          {state.camera.latencyMs} ms
        </div>
        <button
          className="video-viewport__nightvision"
          type="button"
          role="switch"
          aria-label="Night vision"
          aria-checked={nightVision}
          onClick={() => setNightVision((enabled) => !enabled)}
        >
          NIGHT VISION {nightVision ? 'ON' : 'OFF'}
        </button>
      </div>
      <VisionOverlay
        camera={state.camera.id}
        targets={state.visionTargets}
      />
      {!state.camera.connected && (
        <div className="video-viewport__lost" role="alert">
          CAMERA LOST
        </div>
      )}
    </section>
  )
}
