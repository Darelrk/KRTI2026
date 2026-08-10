import type { CameraId, VisionTarget } from '../domain/flight'

const FRAME_WIDTH = 1920
const FRAME_HEIGHT = 1080

function labelFor(target: VisionTarget) {
  const name = target.className.replace('_', ' ').toUpperCase()
  const confidence = `${Math.round(target.confidence * 100)}%`
  return target.className === 'aruco' && target.markerId !== undefined
    ? `${name} ${confidence} · ID ${target.markerId}`
    : `${name} ${confidence}`
}

export function VisionOverlay({
  camera,
  targets,
}: {
  camera: CameraId
  targets: VisionTarget[]
}) {
  const visible = targets.filter((target) => target.camera === camera)
  return (
    <svg
      aria-label={`${visible.length} vision targets`}
      className="vision-overlay"
      preserveAspectRatio="xMidYMid meet"
      viewBox={`0 0 ${FRAME_WIDTH} ${FRAME_HEIGHT}`}
    >
      {visible.map((target) => {
        const box = target.box
        const path = target.path?.map(({ x, y }) => ({
          x: x * FRAME_WIDTH,
          y: y * FRAME_HEIGHT,
        }))
        const labelX = box
          ? box.x * FRAME_WIDTH
          : (path?.[0]?.x ?? 0)
        const labelY = box
          ? box.y * FRAME_HEIGHT
          : (path?.[0]?.y ?? 0)
        return (
          <g
            key={target.id}
            aria-label={`${target.className} target`}
            className={`vision-target vision-target--${target.className}`}
          >
            {box && (
              <rect
                height={box.height * FRAME_HEIGHT}
                vectorEffect="non-scaling-stroke"
                width={box.width * FRAME_WIDTH}
                x={box.x * FRAME_WIDTH}
                y={box.y * FRAME_HEIGHT}
              />
            )}
            {path && (
              <polyline
                aria-label={`Detected mission ${target.className}`}
                fill="none"
                points={path.map(({ x, y }) => `${x},${y}`).join(' ')}
                vectorEffect="non-scaling-stroke"
              />
            )}
            <text x={labelX} y={Math.max(28, labelY - 10)}>
              {labelFor(target)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
