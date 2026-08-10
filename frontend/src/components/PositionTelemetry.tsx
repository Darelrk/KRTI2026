import type { TelemetryEvent } from '../domain/flight'

function signed(value: number, digits = 1) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}°`
}

function heading(value: number) {
  return `${String(Math.round(((value % 360) + 360) % 360)).padStart(3, '0')}°`
}

function DataItem({ label, value }: { label: string; value: string }) {
  return <span>{label} {value}</span>
}

export function PositionTelemetry({
  telemetry,
}: {
  telemetry: TelemetryEvent | null
}) {
  if (!telemetry) {
    return (
      <section className="position-telemetry" aria-label="Position telemetry">
        <h2>Position & attitude</h2>
        <strong>NO DATA</strong>
      </section>
    )
  }
  const hasGps = telemetry.latitude !== null && telemetry.longitude !== null
  return (
    <section className="position-telemetry" aria-label="Position telemetry">
      <h2>Position & attitude</h2>
      {!hasGps && <strong>GPS NO FIX</strong>}
      <div className="position-telemetry__grid">
        <DataItem
          label="LAT"
          value={hasGps ? telemetry.latitude!.toFixed(6) : 'NO DATA'}
        />
        <DataItem
          label="LON"
          value={hasGps ? telemetry.longitude!.toFixed(6) : 'NO DATA'}
        />
        <DataItem
          label="LOCAL X"
          value={
            telemetry.localXM === null
              ? 'NO DATA'
              : `${telemetry.localXM.toFixed(2)} m`
          }
        />
        <DataItem
          label="LOCAL Y"
          value={
            telemetry.localYM === null
              ? 'NO DATA'
              : `${telemetry.localYM.toFixed(2)} m`
          }
        />
        <DataItem label="ALT" value={`${telemetry.altitudeM.toFixed(1)} m`} />
        <DataItem
          label="RANGE"
          value={
            telemetry.rangefinderM === null
              ? 'NO DATA'
              : `${telemetry.rangefinderM.toFixed(1)} m`
          }
        />
        <DataItem
          label="SPEED"
          value={`${telemetry.groundSpeedMps.toFixed(1)} m/s`}
        />
        <DataItem label="HDG" value={heading(telemetry.headingDeg)} />
        <DataItem label="ROLL" value={signed(telemetry.rollDeg)} />
        <DataItem label="PITCH" value={signed(telemetry.pitchDeg)} />
        <DataItem label="YAW" value={heading(telemetry.yawDeg)} />
        <DataItem
          label="GPS"
          value={
            hasGps
              ? `FIX ${telemetry.gpsFix} · SAT ${telemetry.gpsSatellites} · HDOP ${telemetry.hdop?.toFixed(1) ?? 'NO DATA'}`
              : 'NO DATA'
          }
        />
      </div>
    </section>
  )
}
