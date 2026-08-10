import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { VisionOverlay } from '../components/VisionOverlay'
import type { VisionTarget } from '../domain/flight'

const person: VisionTarget = {
  id: 'person-1',
  timestampMs: 1,
  frameId: 12,
  camera: 'front',
  className: 'person',
  confidence: 0.91,
  box: { x: 0.25, y: 0.5, width: 0.1, height: 0.2 },
}

const targets: VisionTarget[] = [
  person,
  {
    id: 'aruco-1',
    timestampMs: 1,
    frameId: 12,
    camera: 'front',
    className: 'aruco',
    confidence: 0.96,
    markerId: 17,
    box: { x: 0.45, y: 0.55, width: 0.08, height: 0.12 },
  },
  {
    id: 'line-1',
    timestampMs: 1,
    frameId: 12,
    camera: 'front',
    className: 'line',
    confidence: 0.88,
    path: [
      { x: 0.1, y: 0.8 },
      { x: 0.5, y: 0.5 },
      { x: 0.9, y: 0.2 },
    ],
  },
  {
    id: 'down-gate',
    timestampMs: 1,
    frameId: 12,
    camera: 'down',
    className: 'gate',
    confidence: 0.9,
    box: { x: 0.2, y: 0.2, width: 0.2, height: 0.4 },
  },
]

describe('VisionOverlay', () => {
  it('maps normalized box geometry onto the 16:9 frame', () => {
    const { container } = render(
      <VisionOverlay camera="front" targets={[person]} />,
    )
    const box = container.querySelector('rect')
    expect(box).toHaveAttribute('x', '480')
    expect(box).toHaveAttribute('y', '540')
    expect(box).toHaveAttribute('width', '192')
    expect(box).toHaveAttribute('height', '216')
  })

  it('renders mission labels, marker IDs, and normalized paths', () => {
    render(<VisionOverlay camera="front" targets={targets} />)
    expect(screen.getByText('PERSON 91%')).toBeVisible()
    expect(screen.getByText('ARUCO 96% · ID 17')).toBeVisible()
    expect(screen.getByLabelText('Detected mission line')).toHaveAttribute(
      'points',
      '192,864 960,540 1728,216',
    )
  })

  it('shows only targets from the active camera', () => {
    render(<VisionOverlay camera="front" targets={targets} />)
    expect(screen.queryByText('GATE 90%')).not.toBeInTheDocument()
    expect(screen.getByLabelText('person target')).toHaveClass(
      'vision-target--person',
    )
  })
})
