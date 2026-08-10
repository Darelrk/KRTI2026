import { Button } from '@carbon/react'
import { Pause, Power, WarningAlt } from '@carbon/icons-react'
import { useState } from 'react'
import type {
  CommandResult,
  CommandType,
  RetryCheckpoint,
} from '../domain/flight'
import { useHoldAction } from '../hooks/use-hold-action'

type Props = {
  disabled: boolean
  armed: boolean
  autonomyReady: boolean
  retryCheckpoint: RetryCheckpoint
  onCommand: (type: CommandType) => void
  result?: CommandResult
}

export function CommandRail({
  disabled,
  armed,
  autonomyReady,
  retryCheckpoint,
  onCommand,
  result,
}: Props) {
  const [retryConfirm, setRetryConfirm] = useState(false)
  const arm = useHoldAction(() => onCommand('arm'))
  const emergencyLand = useHoldAction(() => onCommand('emergency_land'))

  return (
    <footer className="command-rail" aria-label="Mission commands">
      <Button
        aria-label="Hold to arm"
        className={arm.holding ? 'is-holding' : ''}
        disabled={disabled || armed}
        onPointerCancel={arm.cancel}
        onPointerDown={arm.start}
        onPointerLeave={arm.cancel}
        onPointerUp={arm.cancel}
        renderIcon={Power}
      >
        Hold to arm
      </Button>
      <Button
        disabled={disabled || !autonomyReady}
        onClick={() => onCommand('enable_autonomy')}
      >
        Enable autonomy
      </Button>
      <Button
        disabled={disabled}
        kind="secondary"
        onClick={() => onCommand('pause_mission')}
        renderIcon={Pause}
      >
        Hold position
      </Button>
      {retryConfirm ? (
        <div className="command-rail__confirm">
          <Button
            kind="danger"
            onClick={() => {
              onCommand('retry')
              setRetryConfirm(false)
            }}
          >
            Confirm retry
          </Button>
          <Button kind="ghost" onClick={() => setRetryConfirm(false)}>
            Cancel
          </Button>
        </div>
      ) : (
        <Button
          disabled={disabled}
          kind="secondary"
          onClick={() => setRetryConfirm(true)}
        >
          Retry mission
        </Button>
      )}
      <span className="command-rail__checkpoint">
        RETRY → {retryCheckpoint}
      </span>
      <Button
        aria-label="Hold to emergency land"
        className={emergencyLand.holding ? 'is-holding' : ''}
        disabled={disabled || !armed}
        kind="danger"
        onPointerCancel={emergencyLand.cancel}
        onPointerDown={emergencyLand.start}
        onPointerLeave={emergencyLand.cancel}
        onPointerUp={emergencyLand.cancel}
        renderIcon={WarningAlt}
      >
        Emergency land
      </Button>
      {retryConfirm && (
        <output className="command-rail__confirm-label" role="status">
          Confirm retry to {retryCheckpoint}
        </output>
      )}
      {result && (
        <output
          className={`command-rail__result command-rail__result--${result.status}`}
          role="status"
        >
          {result.status === 'accepted'
            ? 'COMMAND ACCEPTED'
            : `${result.status.toUpperCase()}: ${result.reason ?? 'No response detail'}`}
        </output>
      )}
    </footer>
  )
}
