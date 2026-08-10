import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { VideoViewport } from '../components/VideoViewport'
import { initialFlightState } from '../domain/flight-reducer'

describe('VideoViewport', () => {
  it('does not render the demo training image', () => {
    const { container } = render(<VideoViewport state={initialFlightState} />)
    expect(container.querySelector('img')).not.toBeInTheDocument()
    expect(screen.getByText('CAMERA LOST')).toBeVisible()
  })

  it('toggles the night vision panel mode', () => {
    render(<VideoViewport state={initialFlightState} />)
    const toggle = screen.getByRole('switch', { name: 'Night vision' })
    const panel = screen.getByRole('region', { name: 'Live camera' })

    expect(toggle).toHaveAttribute('aria-checked', 'false')
    expect(panel).not.toHaveClass('video-viewport--nightvision')
    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-checked', 'true')
    expect(toggle).toHaveTextContent('NIGHT VISION ON')
    expect(panel).toHaveClass('video-viewport--nightvision')
  })
})
