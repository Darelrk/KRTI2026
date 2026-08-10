import { Button } from '@carbon/react'
import { WarningAlt } from '@carbon/icons-react'
import type { LinkState, SafetyState } from '../domain/flight'

export function SafetyEventQueue({
  link,
  safety,
  onAcknowledgePerson,
}: {
  link: LinkState
  safety: SafetyState
  onAcknowledgePerson: () => void
}) {
  const hasWarning =
    link !== 'connected' ||
    safety.elsState !== 'standby' ||
    safety.personWarning ||
    safety.obstacleWarning

  return (
    <section className="safety-event-queue" aria-labelledby="safety-events-title">
      <h2 id="safety-events-title">Safety events</h2>
      {!hasWarning && <p>SAFETY NOMINAL</p>}
      {safety.elsState === 'active' && (
        <article className="safety-event safety-event--critical">
          <WarningAlt aria-hidden="true" />
          <strong>ELS ACTIVE</strong>
          <span>Flight-controller emergency landing state.</span>
        </article>
      )}
      {link !== 'connected' && safety.elsState !== 'active' && (
        <article className="safety-event safety-event--critical">
          <WarningAlt aria-hidden="true" />
          <strong>LINK {link.toUpperCase()}</strong>
          <span>Lost contact {safety.linkLostSeconds}s.</span>
        </article>
      )}
      {safety.obstacleWarning && (
        <article className="safety-event safety-event--critical">
          <WarningAlt aria-hidden="true" />
          <strong>COLLISION CLEARANCE LOW</strong>
        </article>
      )}
      {safety.personWarning && (
        <article className="safety-event safety-event--person">
          <WarningAlt aria-hidden="true" />
          <strong>PERSON IN FLIGHT AREA</strong>
          {safety.personAcknowledged ? (
            <span>PERSON WARNING ACKNOWLEDGED</span>
          ) : (
            <Button
              kind="danger--tertiary"
              onClick={onAcknowledgePerson}
              size="sm"
            >
              Acknowledge person warning
            </Button>
          )}
        </article>
      )}
    </section>
  )
}
