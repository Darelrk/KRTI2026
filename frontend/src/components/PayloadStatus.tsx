import { Package } from '@carbon/icons-react'
import type { PayloadState } from '../domain/flight'

export function PayloadStatus({ state }: { state: PayloadState }) {
  return (
    <section className="payload-status" aria-label="Medical payload status">
      <Package aria-hidden="true" size={20} />
      <div>
        <span>Medical payload</span>
        <strong>{state.toUpperCase()}</strong>
      </div>
    </section>
  )
}
