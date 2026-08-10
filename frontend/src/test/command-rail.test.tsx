import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { CommandRail } from '../components/CommandRail'

afterEach(() => vi.useRealTimers())

const renderCommands = (overrides = {}) =>
  render(
    <CommandRail
      disabled={false}
      armed={false}
      autonomyReady
      retryCheckpoint="WP2"
      onCommand={vi.fn()}
      {...overrides}
    />,
  )

it('does not arm before the full hold duration', () => {
  vi.useFakeTimers()
  const onCommand = vi.fn()
  renderCommands({ onCommand })
  const arm = screen.getByRole('button', { name: 'Hold to arm' })

  fireEvent.pointerDown(arm)
  act(() => vi.advanceTimersByTime(1_499))
  expect(onCommand).not.toHaveBeenCalled()
  act(() => vi.advanceTimersByTime(1))
  expect(onCommand).toHaveBeenCalledWith('arm')
})

it('requires autonomy readiness and never renders GPS or RTL controls', () => {
  renderCommands({ autonomyReady: false })
  expect(screen.getByRole('button', { name: 'Enable autonomy' })).toBeDisabled()
  expect(screen.queryByText('RTL')).not.toBeInTheDocument()
  expect(screen.queryByText('Takeoff')).not.toBeInTheDocument()
})

it('confirms retry checkpoint before sending it', () => {
  const onCommand = vi.fn()
  renderCommands({ onCommand })
  fireEvent.click(screen.getByRole('button', { name: 'Retry mission' }))
  expect(screen.getByText('Confirm retry to WP2')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Confirm retry' }))
  expect(onCommand).toHaveBeenCalledWith('retry')
})

it('uses hold-to-confirm emergency land and shows backend rejection', () => {
  vi.useFakeTimers()
  const onCommand = vi.fn()
  renderCommands({
    armed: true,
    onCommand,
    result: {
      commandId: 'command-1',
      status: 'rejected',
      reason: 'Emergency land unavailable',
    },
  })
  const land = screen.getByRole('button', { name: 'Hold to emergency land' })
  fireEvent.pointerDown(land)
  act(() => vi.advanceTimersByTime(1_500))
  expect(onCommand).toHaveBeenCalledWith('emergency_land')
  expect(screen.getByRole('status')).toHaveTextContent(
    'REJECTED: Emergency land unavailable',
  )
})
