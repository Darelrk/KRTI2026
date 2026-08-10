# KRTI UAV Dashboard Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun dashboard operator KRTI video-first dengan TanStack Start, IBM Carbon dark theme, mock flight adapter, telemetry, candidate detection, mission controls terbatas, dan seluruh failure state tanpa backend nyata.

**Architecture:** Satu route mission operations memakai Carbon `g100`. TanStack Query menangani snapshot/command mutation, native event subscription menerima data mock real-time, dan React reducer menangani UI state. Kontrak adapter sengaja identik dengan backend WebSocket/WebRTC/MAVLink tahap berikutnya.

**Tech Stack:** TanStack Start React, TypeScript, TanStack Query, IBM Carbon React v11, Carbon Icons, Sass, MapLibre GL, Vitest, Testing Library, Chrome DevTools.

**Source Spec:** `docs/superpowers/specs/2026-08-10-krti-uav-dashboard-design.md`

**Repository note:** `D:/KRTI` belum merupakan Git repository. Plan ini tidak melakukan commit dan tidak menginisialisasi Git tanpa instruksi pengguna.

---

## File Structure

```text
frontend/
├── package.json
├── vite.config.ts
├── public/demo/test-frame.jpg
└── src/
    ├── routes/
    │   ├── __root.tsx
    │   └── index.tsx
    ├── styles/
    │   └── app.scss
    ├── domain/
    │   ├── flight.ts
    │   └── flight-reducer.ts
    ├── data/
    │   ├── flight-adapter.ts
    │   └── mock-flight-adapter.ts
    ├── hooks/
    │   ├── use-flight-session.ts
    │   └── use-hold-action.ts
    ├── integrations/
    │   └── query-provider.tsx
    ├── components/
    │   ├── DashboardShell.tsx
    │   ├── StatusRail.tsx
    │   ├── VideoViewport.tsx
    │   ├── DetectionOverlay.tsx
    │   ├── MiniMap.tsx
    │   ├── DetectionQueue.tsx
    │   ├── MissionProgress.tsx
    │   ├── CommandRail.tsx
    │   └── CriticalAlert.tsx
    └── test/
        ├── setup.ts
        ├── flight-reducer.test.ts
        ├── detection-queue.test.tsx
        └── command-rail.test.tsx

```

## Task 1: Scaffold TanStack Start and Dependencies

**Files:**
- Create: `frontend/` through official TanStack CLI
- Modify: `frontend/package.json`
- Copy: `test_frame.jpg` → `frontend/public/demo/test-frame.jpg`

- [ ] **Step 1: Scaffold the official application**

Run from `D:/KRTI`:

```bash
npx @tanstack/cli@latest create
```

Choose these exact options:

```text
Project directory: frontend
Framework: TanStack Start
Language: TypeScript
Package manager: npm
Add-ons: none
Git initialization: no
```

Expected: `frontend/src/routes/__root.tsx`, `frontend/src/routes/index.tsx`, and `frontend/vite.config.ts` exist.

- [ ] **Step 2: Install runtime dependencies**

```bash
npm install @carbon/react @carbon/icons-react @tanstack/react-query maplibre-gl sass
```

Run with `cwd=D:/KRTI/frontend`.

Expected: dependencies appear in `frontend/package.json`.

- [ ] **Step 3: Install focused test dependencies**

```bash
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
npm pkg set scripts.test="vitest" scripts.test:run="vitest run"
```

Expected: `npm run test:run` starts Vitest successfully even before tests are added.

- [ ] **Step 4: Copy the real aerial frame**

```bash
mkdir -p public/demo
cp ../test_frame.jpg public/demo/test-frame.jpg
```

Expected: `frontend/public/demo/test-frame.jpg` exists and is the real aerial source frame.

- [ ] **Step 5: Configure Vitest in the existing Vite config**

Add to `frontend/vite.config.ts` without changing generated TanStack plugins:

```ts
/// <reference types="vitest/config" />

// inside defineConfig({...})
test: {
  environment: 'jsdom',
  setupFiles: ['./src/test/setup.ts'],
},
```

Create `frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 6: Keep browser verification dependency-free**

Chrome DevTools/CDP is supplied by the development environment and is not installed in `package.json`.

Run:

```bash
npm pkg get devDependencies
```

Expected: browser automation packages are absent; verification remains external to the application.

- [ ] **Step 7: Smoke the scaffold**

Run:

```bash
npm run dev -- --host 127.0.0.1
```

Expected: generated TanStack Start page opens at `http://127.0.0.1:3000`.

## Task 2: Carbon Theme and Dashboard Shell

**Files:**
- Modify: `frontend/src/routes/__root.tsx`
- Modify: `frontend/src/routes/index.tsx`
- Create: `frontend/src/styles/app.scss`
- Create: `frontend/src/components/DashboardShell.tsx`

- [ ] **Step 1: Load Carbon and g100 tokens**

Create `frontend/src/styles/app.scss`:

```scss
@use '@carbon/react';
@use '@carbon/styles/scss/theme';
@use '@carbon/styles/scss/themes';

:root,
[data-carbon-theme='g100'] {
  @include theme.theme(themes.$g100);
}

* { box-sizing: border-box; }
html, body, #root { margin: 0; min-height: 100%; }
body {
  background: var(--cds-background);
  color: var(--cds-text-primary);
  overflow: hidden;
}
button, input { font: inherit; }

.mission-dashboard {
  display: grid;
  grid-template-rows: 3rem minmax(0, 1fr) 4rem;
  min-height: 100dvh;
  background: var(--cds-background);
}

.mission-dashboard__main {
  display: grid;
  grid-template-columns: minmax(0, 2.1fr) minmax(20rem, 1fr);
  min-height: 0;
  border-block: 1px solid var(--cds-border-subtle-01);
}

@media (max-width: 85.375rem) {
  .mission-dashboard__main {
    grid-template-columns: minmax(0, 1.8fr) 20rem;
  }
}
```

- [ ] **Step 2: Apply global styles and document metadata**

Update `frontend/src/routes/__root.tsx` using the generated route shell, preserving `HeadContent`, `Outlet`, and `Scripts`. Add:

```tsx
import '../styles/app.scss'
```

Set metadata:

```tsx
head: () => ({
  meta: [
    { charSet: 'utf-8' },
    { name: 'viewport', content: 'width=device-width, initial-scale=1' },
    { name: 'theme-color', content: '#161616' },
  ],
  links: [],
  scripts: [],
  title: 'KRTI UAV Mission Operations',
})
```

Set the generated `<body>` to:

```tsx
<body data-carbon-theme="g100">
  {children}
  <Scripts />
</body>
```

- [ ] **Step 3: Create structural shell**

Create `frontend/src/components/DashboardShell.tsx`:

```tsx
import type { ReactNode } from 'react'

type Props = {
  status: ReactNode
  video: ReactNode
  sidebar: ReactNode
  commands: ReactNode
  alert?: ReactNode
}

export function DashboardShell({ status, video, sidebar, commands, alert }: Props) {
  return (
    <main className="mission-dashboard">
      {alert}
      {status}
      <section className="mission-dashboard__main">
        {video}
        {sidebar}
      </section>
      {commands}
    </main>
  )
}
```

- [ ] **Step 4: Replace generated route content with the dashboard shell**

Update `frontend/src/routes/index.tsx`:

```tsx
import { createFileRoute } from '@tanstack/react-router'
import { DashboardShell } from '../components/DashboardShell'

export const Route = createFileRoute('/')({ component: MissionOperationsPage })

function MissionOperationsPage() {
  return (
    <DashboardShell
      status={<div>Status rail</div>}
      video={<div>Video viewport</div>}
      sidebar={<aside>Mission sidebar</aside>}
      commands={<div>Command rail</div>}
    />
  )
}
```

- [ ] **Step 5: Run the app**

Run `npm run dev -- --host 127.0.0.1`.

Expected: a full-height three-row Carbon-dark shell with a video/sidebar split and no vertical page scroll at 1366×768.

## Task 3: Domain Contracts and Flight Reducer

**Files:**
- Create: `frontend/src/domain/flight.ts`
- Create: `frontend/src/domain/flight-reducer.ts`
- Create: `frontend/src/test/flight-reducer.test.ts`

- [ ] **Step 1: Write reducer contract tests**

Create `frontend/src/test/flight-reducer.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { initialFlightState, reduceFlightEvent } from '../domain/flight-reducer'

const telemetry = {
  type: 'telemetry' as const,
  seq: 1,
  timestampMs: 1_000,
  armed: false,
  mode: 'STABILIZE',
  batteryPercent: 68,
  voltage: 15.8,
  gpsSatellites: 14,
  latitude: -7.77,
  longitude: 110.37,
  altitudeM: 12.4,
  groundSpeedMps: 3.2,
  headingDeg: 120,
}

describe('flight reducer', () => {
  it('updates telemetry and link timestamp', () => {
    const next = reduceFlightEvent(initialFlightState, telemetry)
    expect(next.telemetry).toEqual(telemetry)
    expect(next.lastEventAt).toBe(1_000)
  })

  it('keeps confirmed detections when a burst trims candidates', () => {
    const confirmed = { id: 'confirmed', status: 'confirmed' as const }
    const candidates = Array.from({ length: 25 }, (_, index) => ({
      id: `candidate-${index}`,
      status: 'candidate' as const,
    }))
    const state = { ...initialFlightState, detections: [confirmed, ...candidates] }
    const next = reduceFlightEvent(state, { type: 'trim_detections', seq: 2, timestampMs: 2_000 })
    expect(next.detections).toContainEqual(confirmed)
    expect(next.detections.filter((item) => item.status === 'candidate')).toHaveLength(20)
  })
})
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
npm run test:run -- src/test/flight-reducer.test.ts
```

Expected: FAIL because domain modules do not exist.

- [ ] **Step 3: Define explicit domain types**

Create `frontend/src/domain/flight.ts`:

```ts
export type LinkState = 'connected' | 'stale' | 'disconnected'
export type DetectionStatus = 'candidate' | 'confirmed' | 'dismissed'
export type CommandType = 'arm' | 'takeoff' | 'start_mission' | 'pause_mission' | 'rtl' | 'land'

export type TelemetryEvent = {
  type: 'telemetry'
  seq: number
  timestampMs: number
  armed: boolean
  mode: string
  batteryPercent: number
  voltage: number
  gpsSatellites: number
  latitude: number
  longitude: number
  altitudeM: number
  groundSpeedMps: number
  headingDeg: number
}

export type Detection = {
  id: string
  status: DetectionStatus
  timestampMs?: number
  frameId?: number
  className?: 'person'
  confidence?: number
  box?: { x: number; y: number; width: number; height: number }
  snapshotUrl?: string
}

export type DetectionEvent = Required<Omit<Detection, 'status'>> & {
  type: 'detection'
  seq: number
  timestampMs: number
  status: 'candidate'
}

export type FlightEvent =
  | TelemetryEvent
  | DetectionEvent
  | { type: 'link'; seq: number; timestampMs: number; state: LinkState }
  | { type: 'camera'; seq: number; timestampMs: number; connected: boolean; latencyMs: number; fps: number }
  | { type: 'mission'; seq: number; timestampMs: number; currentWaypoint: number; totalWaypoints: number; elapsedSeconds: number }
  | { type: 'trim_detections'; seq: number; timestampMs: number }

export type CommandRequest = { commandId: string; type: CommandType }
export type CommandResult = { commandId: string; status: 'accepted' | 'rejected' | 'unknown'; reason?: string }
```

- [ ] **Step 4: Implement the reducer**

Create `frontend/src/domain/flight-reducer.ts`:

```ts
import type { Detection, FlightEvent, LinkState, TelemetryEvent } from './flight'

export type FlightState = {
  telemetry: TelemetryEvent | null
  link: LinkState
  camera: { connected: boolean; latencyMs: number; fps: number }
  mission: { currentWaypoint: number; totalWaypoints: number; elapsedSeconds: number }
  detections: Detection[]
  lastEventAt: number
}

export const initialFlightState: FlightState = {
  telemetry: null,
  link: 'disconnected',
  camera: { connected: false, latencyMs: 0, fps: 0 },
  mission: { currentWaypoint: 0, totalWaypoints: 0, elapsedSeconds: 0 },
  detections: [],
  lastEventAt: 0,
}

export function reduceFlightEvent(state: FlightState, event: FlightEvent): FlightState {
  if (event.type === 'telemetry') return { ...state, telemetry: event, lastEventAt: event.timestampMs }
  if (event.type === 'link') return { ...state, link: event.state, lastEventAt: event.timestampMs }
  if (event.type === 'camera') return { ...state, camera: event, lastEventAt: event.timestampMs }
  if (event.type === 'mission') return { ...state, mission: event, lastEventAt: event.timestampMs }
  if (event.type === 'detection') {
    return { ...state, detections: [{ ...event, status: 'candidate' }, ...state.detections], lastEventAt: event.timestampMs }
  }
  const confirmed = state.detections.filter((item) => item.status === 'confirmed')
  const candidates = state.detections.filter((item) => item.status === 'candidate').slice(0, 20)
  return { ...state, detections: [...confirmed, ...candidates], lastEventAt: event.timestampMs }
}
```

- [ ] **Step 5: Run reducer tests**

Run `npm run test:run -- src/test/flight-reducer.test.ts`.

Expected: both tests PASS.

## Task 4: Adapter Contract, Mock Flight, and Query Provider

**Files:**
- Create: `frontend/src/data/flight-adapter.ts`
- Create: `frontend/src/data/mock-flight-adapter.ts`
- Create: `frontend/src/integrations/query-provider.tsx`
- Create: `frontend/src/hooks/use-flight-session.ts`
- Modify: `frontend/src/routes/__root.tsx`

- [ ] **Step 1: Define the replaceable adapter**

Create `frontend/src/data/flight-adapter.ts`:

```ts
import type { CommandRequest, CommandResult, FlightEvent } from '../domain/flight'
import type { FlightState } from '../domain/flight-reducer'

export interface FlightAdapter {
  getSnapshot(): Promise<FlightState>
  subscribe(listener: (event: FlightEvent) => void): () => void
  sendCommand(command: CommandRequest): Promise<CommandResult>
}
```

- [ ] **Step 2: Implement deterministic mock behavior**

Create `frontend/src/data/mock-flight-adapter.ts`. Use one interval at 200 ms, emit telemetry every fifth tick, decrement battery every 300 ticks, emit a candidate detection every 50 ticks, and clear the interval on unsubscribe:

```ts
import type { FlightAdapter } from './flight-adapter'
import type { CommandRequest, FlightEvent } from '../domain/flight'
import { initialFlightState } from '../domain/flight-reducer'

export const mockFlightAdapter: FlightAdapter = {
  async getSnapshot() {
    return {
      ...initialFlightState,
      link: 'connected',
      camera: { connected: true, latencyMs: 112, fps: 24 },
      mission: { currentWaypoint: 3, totalWaypoints: 8, elapsedSeconds: 253 },
    }
  },
  subscribe(listener) {
    let tick = 0
    let seq = 0
    const timer = window.setInterval(() => {
      tick += 1
      const now = Date.now()
      if (tick % 5 === 0) {
        listener({
          type: 'telemetry', seq: ++seq, timestampMs: now,
          armed: true, mode: 'AUTO', batteryPercent: Math.max(19, 68 - Math.floor(tick / 300)),
          voltage: 15.8, gpsSatellites: 14, latitude: -7.7706,
          longitude: 110.3776, altitudeM: 12.4, groundSpeedMps: 3.2, headingDeg: tick % 360,
        })
      }
      if (tick % 50 === 0) {
        listener({
          type: 'detection', seq: ++seq, timestampMs: now,
          id: crypto.randomUUID(), frameId: tick, className: 'person', confidence: 0.84,
          status: 'candidate', box: { x: 0.56, y: 0.28, width: 0.08, height: 0.22 },
          snapshotUrl: '/demo/test-frame.jpg',
        })
      }
    }, 200)
    listener({ type: 'link', seq: ++seq, timestampMs: Date.now(), state: 'connected' })
    listener({ type: 'camera', seq: ++seq, timestampMs: Date.now(), connected: true, latencyMs: 112, fps: 24 })
    listener({ type: 'mission', seq: ++seq, timestampMs: Date.now(), currentWaypoint: 3, totalWaypoints: 8, elapsedSeconds: 253 })
    return () => window.clearInterval(timer)
  },
  async sendCommand(command: CommandRequest) {
    await new Promise((resolve) => window.setTimeout(resolve, 350))
    return { commandId: command.commandId, status: 'accepted' as const }
  },
}
```

- [ ] **Step 3: Add the TanStack Query provider**

Create `frontend/src/integrations/query-provider.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'

export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 1_000, retry: false }, mutations: { retry: false } },
  }))
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
```

Wrap `{children}` inside the generated root document with `<QueryProvider>`.

- [ ] **Step 4: Create the session hook**

Create `frontend/src/hooks/use-flight-session.ts`:

```ts
import { useMutation, useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useReducer, useState } from 'react'
import { mockFlightAdapter } from '../data/mock-flight-adapter'
import type { DetectionStatus } from '../domain/flight'
import { initialFlightState, reduceFlightEvent } from '../domain/flight-reducer'

export function useFlightSession() {
  const snapshot = useQuery({ queryKey: ['flight', 'snapshot'], queryFn: () => mockFlightAdapter.getSnapshot() })
  const [state, dispatch] = useReducer(reduceFlightEvent, initialFlightState)
  const [now, setNow] = useState(Date.now)

  useEffect(() => mockFlightAdapter.subscribe(dispatch), [])
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1_000)
    return () => window.clearInterval(timer)
  }, [])

  const command = useMutation({ mutationFn: mockFlightAdapter.sendCommand })
  const current = state.lastEventAt === 0 && snapshot.data ? snapshot.data : state
  const liveState = current.link === 'connected' && now - current.lastEventAt > 2_000
    ? { ...current, link: 'stale' as const }
    : current
  const updateDetectionStatus = useCallback((id: string, status: DetectionStatus) => {
    dispatch({ type: 'set_detection_status', id, status })
  }, [])
  return { state: liveState, command, updateDetectionStatus }
}
```

- [ ] **Step 5: Run typecheck/build**

Run:

```bash
npm run build
```

Expected: production build succeeds and the adapter subscription has cleanup through the returned function.

## Task 5: Status Rail and Critical Alerts

**Files:**
- Create: `frontend/src/components/StatusRail.tsx`
- Create: `frontend/src/components/CriticalAlert.tsx`
- Modify: `frontend/src/styles/app.scss`

- [ ] **Step 1: Implement semantic alert selection**

Create `frontend/src/components/CriticalAlert.tsx`:

```tsx
import { InlineNotification } from '@carbon/react'
import type { FlightState } from '../domain/flight-reducer'

export function CriticalAlert({ state }: { state: FlightState }) {
  const telemetry = state.telemetry
  if (state.link === 'disconnected') return <InlineNotification lowContrast={false} kind="error" title="MAVLink disconnected" subtitle="Use RC and verify backend link." hideCloseButton />
  if (state.link === 'stale') return <InlineNotification lowContrast={false} kind="warning" title="Telemetry stale" subtitle="Mission commands are locked." hideCloseButton />
  if (!state.camera.connected) return <InlineNotification lowContrast={false} kind="error" title="Camera lost" subtitle="Reconnecting WebRTC stream." hideCloseButton />
  if (telemetry && telemetry.batteryPercent < 20) return <InlineNotification lowContrast={false} kind="error" title="Battery critical" subtitle="RTL is recommended." hideCloseButton />
  return null
}
```

- [ ] **Step 2: Implement the fixed status rail**

Create `frontend/src/components/StatusRail.tsx`:

```tsx
import { BatteryFull, ConnectionSignal, Location, Time } from '@carbon/icons-react'
import type { ReactNode } from 'react'
import type { FlightState } from '../domain/flight-reducer'

function Item({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return <span className="status-rail__item">{icon}{children}</span>
}

export function StatusRail({ state }: { state: FlightState }) {
  const t = state.telemetry
  return (
    <header className="status-rail" aria-label="Flight status">
      <strong>KRTI UAV</strong>
      <Item icon={<ConnectionSignal size={16} />}><span aria-live="polite">{state.link.toUpperCase()}</span></Item>
      <span>{t?.mode ?? 'NO DATA'}</span>
      <span>{t?.armed ? 'ARMED' : 'DISARMED'}</span>
      <Item icon={<Location size={16} />}>GPS {t?.gpsSatellites ?? 0}</Item>
      <Item icon={<BatteryFull size={16} />}>{t?.voltage.toFixed(1) ?? '--'} V / <span aria-live="polite">{t?.batteryPercent ?? 0}%</span></Item>
      <Item icon={<Time size={16} />}><time>{new Date().toLocaleTimeString('en-GB')}</time></Item>
    </header>
  )
}
```

- [ ] **Step 3: Add Carbon-aligned rail styles**

Append to `app.scss`:

```scss
.status-rail {
  display: grid;
  grid-template-columns: 9rem repeat(6, minmax(max-content, 1fr)) max-content;
  align-items: center;
  gap: 1rem;
  padding-inline: 1rem;
  background: var(--cds-layer-01);
  border-bottom: 1px solid var(--cds-border-subtle-01);
  font-family: 'IBM Plex Mono', monospace;
  font-size: .75rem;
  line-height: 1;
  white-space: nowrap;
}
```

- [ ] **Step 4: Browser check**

Expected: status rail remains one line at 1366×768, uses no pills, and every critical state has icon/text in addition to color.

## Task 6: Video Viewport and Normalized Detection Overlay

**Files:**
- Create: `frontend/src/components/DetectionOverlay.tsx`
- Create: `frontend/src/components/VideoViewport.tsx`
- Modify: `frontend/src/styles/app.scss`

- [ ] **Step 1: Implement SVG overlay**

Create `frontend/src/components/DetectionOverlay.tsx`:

```tsx
import type { Detection } from '../domain/flight'

export function DetectionOverlay({ detections }: { detections: Detection[] }) {
  return (
    <svg className="detection-overlay" viewBox="0 0 1 1" preserveAspectRatio="none" aria-label={`${detections.length} detections`}>
      {detections.filter((item) => item.status !== 'dismissed' && item.box).map((item) => {
        const box = item.box!
        return (
          <g key={item.id} className={`detection detection--${item.status}`}>
            <rect x={box.x} y={box.y} width={box.width} height={box.height} vectorEffect="non-scaling-stroke" />
            <text x={box.x} y={Math.max(0.025, box.y - 0.008)}>{`PERSON ${Math.round((item.confidence ?? 0) * 100)}%`}</text>
          </g>
        )
      })}
    </svg>
  )
}
```

- [ ] **Step 2: Implement the camera surface**

Create `frontend/src/components/VideoViewport.tsx`:

```tsx
import type { FlightState } from '../domain/flight-reducer'
import { DetectionOverlay } from './DetectionOverlay'

export function VideoViewport({ state }: { state: FlightState }) {
  return (
    <section className="video-viewport" aria-label="Live camera">
      <img src="/demo/test-frame.jpg" alt="Aerial camera preview" />
      <DetectionOverlay detections={state.detections} />
      <div className="video-viewport__metrics">{state.camera.fps} FPS / {state.camera.latencyMs} ms</div>
      {!state.camera.connected && <div className="video-viewport__lost" role="alert">CAMERA LOST</div>}
    </section>
  )
}
```

- [ ] **Step 3: Add overlay styles**

Append to `app.scss`:

```scss
.video-viewport { position: relative; min-width: 0; min-height: 0; overflow: hidden; background: #000; }
.video-viewport > img { width: 100%; height: 100%; object-fit: contain; display: block; }
.detection-overlay { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.detection rect { fill: transparent; stroke: var(--cds-support-warning); stroke-width: 2px; }
.detection--confirmed rect { stroke: var(--cds-link-primary); }
.detection text { fill: var(--cds-text-on-color); font-size: .022px; font-family: 'IBM Plex Mono', monospace; paint-order: stroke; stroke: #000; stroke-width: .004px; }
.video-viewport__metrics { position: absolute; inset: 1rem auto auto 1rem; padding: .25rem .5rem; background: rgb(22 22 22 / 80%); font-family: 'IBM Plex Mono', monospace; }
.video-viewport__lost { position: absolute; inset: 0; display: grid; place-items: center; background: rgb(22 22 22 / 72%); color: var(--cds-support-error); font-size: 1.5rem; font-weight: 600; }
```

- [ ] **Step 4: Visual smoke**

Expected: real aerial frame fills the main surface without distortion, boxes align with normalized coordinates, candidate is amber, confirmed is blue, and no overlay intercepts pointer input.

## Task 7: Mission Sidebar

**Files:**
- Create: `frontend/src/components/MiniMap.tsx`
- Create: `frontend/src/components/DetectionQueue.tsx`
- Create: `frontend/src/components/MissionProgress.tsx`
- Create: `frontend/src/test/detection-queue.test.tsx`
- Modify: `frontend/src/styles/app.scss`

- [ ] **Step 1: Write detection queue behavior test**

Create `frontend/src/test/detection-queue.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { DetectionQueue } from '../components/DetectionQueue'

it('confirms a candidate explicitly', async () => {
  const onStatus = vi.fn()
  render(<DetectionQueue detections={[{ id: 'd1', status: 'candidate', confidence: 0.84, snapshotUrl: '/demo/test-frame.jpg' }]} onStatus={onStatus} />)
  await userEvent.click(screen.getByRole('button', { name: 'Confirm detection' }))
  expect(onStatus).toHaveBeenCalledWith('d1', 'confirmed')
})
```

- [ ] **Step 2: Run the test to verify failure**

Run `npm run test:run -- src/test/detection-queue.test.tsx`.

Expected: FAIL because `DetectionQueue` does not exist.

- [ ] **Step 3: Implement detection queue**

Create `DetectionQueue.tsx` with signature:

```tsx
import { Button } from '@carbon/react'
import type { Detection, DetectionStatus } from '../domain/flight'

export function DetectionQueue({ detections, onStatus }: {
  detections: Detection[]
  onStatus: (id: string, status: DetectionStatus) => void
}) {
  const visible = detections.filter((item) => item.status !== 'dismissed')
  return (
    <section className="detection-queue" aria-labelledby="detections-title">
      <h2 id="detections-title">Detections ({visible.length})</h2>
      {visible.length === 0 && <p>NO CANDIDATES</p>}
      {visible.map((item) => (
        <article key={item.id}>
          <img src={item.snapshotUrl} alt="Detected person candidate" />
          <strong>{Math.round((item.confidence ?? 0) * 100)}%</strong>
          {item.status === 'candidate' && <>
            <Button size="sm" onClick={() => onStatus(item.id, 'confirmed')}>Confirm detection</Button>
            <Button kind="ghost" size="sm" onClick={() => onStatus(item.id, 'dismissed')}>Dismiss detection</Button>
          </>}
          {item.status === 'confirmed' && <span>CONFIRMED</span>}
        </article>
      ))}
    </section>
  )
}
```

- [ ] **Step 4: Implement compact mission progress**

Create `frontend/src/components/MissionProgress.tsx`:

```tsx
import { ProgressBar } from '@carbon/react'
import type { FlightState } from '../domain/flight-reducer'

export function MissionProgress({ mission }: { mission: FlightState['mission'] }) {
  const value = mission.totalWaypoints === 0 ? 0 : mission.currentWaypoint / mission.totalWaypoints * 100
  const minutes = Math.floor(mission.elapsedSeconds / 60)
  const seconds = String(mission.elapsedSeconds % 60).padStart(2, '0')
  return (
    <section className="mission-progress" aria-labelledby="mission-progress-title">
      <h2 id="mission-progress-title">Mission progress</h2>
      <ProgressBar label={`WP ${mission.currentWaypoint}/${mission.totalWaypoints}`} value={value} max={100} />
      <time>{minutes}:{seconds}</time>
    </section>
  )
}
```

- [ ] **Step 5: Implement MapLibre map with fallback**

Create `frontend/src/components/MiniMap.tsx`:

```tsx
import 'maplibre-gl/dist/maplibre-gl.css'
import maplibregl, { type GeoJSONSource, type Map, type StyleSpecification } from 'maplibre-gl'
import { useEffect, useRef } from 'react'
import type { TelemetryEvent } from '../domain/flight'

const style: StyleSpecification = {
  version: 8,
  sources: { osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256 } },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
}

export function MiniMap({ telemetry }: { telemetry: TelemetryEvent | null }) {
  const element = useRef<HTMLDivElement>(null)
  const mapRef = useRef<Map | null>(null)

  useEffect(() => {
    if (!element.current || !telemetry || mapRef.current) return
    const coordinates: [number, number] = [telemetry.longitude, telemetry.latitude]
    const map = new maplibregl.Map({ container: element.current, style, center: coordinates, zoom: 16, attributionControl: false })
    mapRef.current = map
    map.on('load', () => {
      map.addSource('uav', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates } } })
      map.addLayer({ id: 'uav', type: 'circle', source: 'uav', paint: { 'circle-radius': 7, 'circle-color': '#0f62fe', 'circle-stroke-color': '#f4f4f4', 'circle-stroke-width': 2 } })
    })
    return () => { map.remove(); mapRef.current = null }
  }, [Boolean(telemetry)])

  useEffect(() => {
    if (!telemetry) return
    const coordinates: [number, number] = [telemetry.longitude, telemetry.latitude]
    const source = mapRef.current?.getSource('uav') as GeoJSONSource | undefined
    source?.setData({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates } })
    mapRef.current?.jumpTo({ center: coordinates })
  }, [telemetry?.latitude, telemetry?.longitude])

  if (!telemetry) return <section className="mini-map mini-map--empty">WAITING FOR GPS</section>
  return <section className="mini-map" aria-label="UAV position map" ref={element} />
}
```

- [ ] **Step 6: Compose sidebar and styles**

Append to `app.scss`:

```scss
.mission-sidebar {
  display: grid;
  grid-template-rows: minmax(12rem, 1fr) minmax(12rem, 1.15fr) auto;
  min-width: 0;
  min-height: 0;
  background: var(--cds-layer-01);
  border-left: 1px solid var(--cds-border-subtle-01);
}
.mission-sidebar > * { min-height: 0; border-bottom: 1px solid var(--cds-border-subtle-01); }
.mini-map { min-height: 12rem; }
.mini-map--empty { display: grid; place-items: center; font-family: 'IBM Plex Mono', monospace; }
.detection-queue { overflow: auto; padding: 1rem; }
.detection-queue article { display: grid; grid-template-columns: 5rem 1fr; gap: .5rem; padding-block: .75rem; }
.detection-queue img { width: 5rem; height: 3rem; object-fit: cover; }
.mission-progress { padding: 1rem; }
```

- [ ] **Step 7: Run queue tests**

Run `npm run test:run -- src/test/detection-queue.test.tsx`.

Expected: PASS.

## Task 8: Hold-to-Confirm Mission Command Rail

**Files:**
- Create: `frontend/src/hooks/use-hold-action.ts`
- Create: `frontend/src/components/CommandRail.tsx`
- Create: `frontend/src/test/command-rail.test.tsx`
- Modify: `frontend/src/styles/app.scss`

- [ ] **Step 1: Write fake-timer safety test**

Create `frontend/src/test/command-rail.test.tsx`:

```tsx
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { CommandRail } from '../components/CommandRail'

afterEach(() => vi.useRealTimers())

it('does not arm before the full hold duration', () => {
  vi.useFakeTimers()
  const onCommand = vi.fn()
  render(<CommandRail disabled={false} armed={false} onCommand={onCommand} />)
  const arm = screen.getByRole('button', { name: 'Hold to arm' })
  fireEvent.pointerDown(arm)
  act(() => vi.advanceTimersByTime(1_499))
  expect(onCommand).not.toHaveBeenCalled()
  act(() => vi.advanceTimersByTime(1))
  expect(onCommand).toHaveBeenCalledWith('arm')
})
```

- [ ] **Step 2: Run test to verify failure**

Run `npm run test:run -- src/test/command-rail.test.tsx`.

Expected: FAIL because the hook and command component do not exist.

- [ ] **Step 3: Implement timer cleanup hook**

Create `frontend/src/hooks/use-hold-action.ts`:

```ts
import { useCallback, useEffect, useRef, useState } from 'react'

export function useHoldAction(onComplete: () => void, durationMs = 1_500) {
  const timer = useRef<number | null>(null)
  const [holding, setHolding] = useState(false)
  const cancel = useCallback(() => {
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = null
    setHolding(false)
  }, [])
  const start = useCallback(() => {
    cancel()
    setHolding(true)
    timer.current = window.setTimeout(() => { timer.current = null; setHolding(false); onComplete() }, durationMs)
  }, [cancel, durationMs, onComplete])
  useEffect(() => cancel, [cancel])
  return { holding, start, cancel }
}
```

- [ ] **Step 4: Implement command rail**

Create `frontend/src/components/CommandRail.tsx`:

```tsx
import { Button } from '@carbon/react'
import { Launch, Pause, Play, Power, Return, WarningAlt } from '@carbon/icons-react'
import { useState } from 'react'
import type { CommandType } from '../domain/flight'
import { useHoldAction } from '../hooks/use-hold-action'

type Props = {
  disabled: boolean
  armed: boolean
  onCommand: (type: CommandType) => void
}

export function CommandRail({ disabled, armed, onCommand }: Props) {
  const [rtlConfirm, setRtlConfirm] = useState(false)
  const arm = useHoldAction(() => onCommand('arm'))
  const land = useHoldAction(() => onCommand('land'))
  return (
    <footer className="command-rail" aria-label="Mission commands">
      <Button renderIcon={Power} disabled={disabled || armed} aria-label="Hold to arm"
        className={arm.holding ? 'is-holding' : ''} onPointerDown={arm.start} onPointerUp={arm.cancel} onPointerLeave={arm.cancel}>
        Hold to arm
      </Button>
      <Button renderIcon={Launch} disabled={disabled || !armed} onClick={() => onCommand('takeoff')}>Takeoff</Button>
      <Button renderIcon={Play} kind="secondary" disabled={disabled || !armed} onClick={() => onCommand('start_mission')}>Start mission</Button>
      <Button renderIcon={Pause} kind="secondary" disabled={disabled} onClick={() => onCommand('pause_mission')}>Pause mission</Button>
      {rtlConfirm
        ? <Button renderIcon={WarningAlt} kind="danger" onClick={() => { onCommand('rtl'); setRtlConfirm(false) }}>Confirm RTL</Button>
        : <Button renderIcon={Return} kind="danger--tertiary" disabled={disabled} onClick={() => setRtlConfirm(true)}>RTL</Button>}
      <Button kind="danger" disabled={disabled || !armed} aria-label="Hold to land"
        className={land.holding ? 'is-holding' : ''} onPointerDown={land.start} onPointerUp={land.cancel} onPointerLeave={land.cancel}>
        Hold to land
      </Button>
    </footer>
  )
}
```

- [ ] **Step 5: Add fixed command styles**

Append to `app.scss`:

```scss
.command-rail {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 1px;
  background: var(--cds-border-subtle-01);
}
.command-rail .cds--btn { width: 100%; max-width: none; min-height: 4rem; white-space: nowrap; }
.command-rail .is-holding { transform: translateY(1px); box-shadow: inset 0 -3px 0 var(--cds-focus); }
```

- [ ] **Step 6: Run safety test**

Run `npm run test:run -- src/test/command-rail.test.tsx`.

Expected: PASS and no pending timers after unmount.

## Task 9: Assemble Live Dashboard State

**Files:**
- Modify: `frontend/src/routes/index.tsx`
- Modify: `frontend/src/domain/flight-reducer.ts`
- Modify: `frontend/src/styles/app.scss`

- [ ] **Step 1: Add detection status reducer action**

In `frontend/src/domain/flight-reducer.ts`, extend the import and add the reducer action type:

```ts
import type { Detection, DetectionStatus, FlightEvent, LinkState, TelemetryEvent } from './flight'

export type FlightAction =
  | FlightEvent
  | { type: 'set_detection_status'; id: string; status: DetectionStatus }
```

Change the reducer parameter from `FlightEvent` to `FlightAction`, then insert this as the first branch:

```ts
if (event.type === 'set_detection_status') {
  return {
    ...state,
    detections: state.detections.map((item) =>
      item.id === event.id ? { ...item, status: event.status } : item,
    ),
  }
}
```

- [ ] **Step 2: Compose all components in route `/`**

Update `index.tsx` to call the session hook and derive the safety gate from already-resolved link state:

```ts
const { state, command, updateDetectionStatus } = useFlightSession()
const commandDisabled = state.link !== 'connected' || (state.telemetry?.gpsSatellites ?? 0) < 8
```

Render:

```tsx
<DashboardShell
  alert={<CriticalAlert state={state} />}
  status={<StatusRail state={state} />}
  video={<VideoViewport state={state} />}
  sidebar={
    <aside className="mission-sidebar">
      <MiniMap telemetry={state.telemetry} />
      <DetectionQueue detections={state.detections} onStatus={updateDetectionStatus} />
      <MissionProgress mission={state.mission} />
    </aside>
  }
  commands={
    <CommandRail
      disabled={commandDisabled}
      armed={state.telemetry?.armed ?? false}
      onCommand={(type) => command.mutate({ commandId: crypto.randomUUID(), type })}
    />
  }
/>
```

Keep detection status in the session reducer rather than component state so overlay and queue remain synchronized.

- [ ] **Step 3: Add 1366×768 and 1920×1080 layout rules**

At 1366 width, sidebar remains 20 rem. At 1920, cap sidebar at 32 rem. At viewport height below 768, reduce command rail to 3.5 rem and status rail to 2.75 rem; never hide critical telemetry. Do not add a mobile-phone layout because the approved target is a laptop ground station.

- [ ] **Step 4: Validate build and unit suite**

Run:

```bash
npm run test:run
npm run build
```

Expected: all tests PASS and production build succeeds.

## Task 10: Chrome DevTools Verification and Safety

**Files:** None.

- [ ] **Step 1: Start the dashboard for DevTools inspection**

Run:

```bash
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:3000/?scenario=detection` through Chrome DevTools/CDP.

- [ ] **Step 2: Verify observable contracts in the DevTools console**

Run:

```js
console.assert(document.querySelector('main'), 'dashboard missing')
console.assert(document.querySelector('[aria-label="Flight status"]')?.textContent?.includes('KRTI UAV'), 'status rail missing')
console.assert(document.querySelector('[aria-label="Live camera"]'), 'camera surface missing')
console.assert([...document.querySelectorAll('button')].some((button) => button.textContent?.includes('Hold to arm')), 'arm control missing')
console.assert([...document.querySelectorAll('button')].some((button) => button.textContent === 'RTL'), 'RTL control missing')
console.assert(document.documentElement.scrollHeight <= innerHeight, 'vertical overflow')
console.assert(document.documentElement.scrollWidth <= innerWidth, 'horizontal overflow')
```

Expected: no assertion failures and no hydration/runtime errors.

- [ ] **Step 3: Drive the UI at both approved sizes**

Use Chrome DevTools responsive viewport at 1366×768 and 1920×1080. Verify:

```text
- Video remains dominant.
- Status rail stays one line.
- Command labels do not wrap.
- No horizontal or vertical dashboard scroll.
- Detection candidate is confirmable/dismissable.
- Critical alert does not cover command rail.
- Keyboard Tab order reaches detections, then commands.
- Focus rings and text contrast remain visible in g100.
```

- [ ] **Step 4: Run all eight mock scenarios**

Exercise:

```text
/?scenario=normal
/?scenario=detection
/?scenario=low-battery
/?scenario=gps-degraded
/?scenario=camera-lost
/?scenario=telemetry-stale
/?scenario=command-rejected
/?scenario=detection-burst
```

Expected: low battery emits 18%, degraded GPS emits 5 satellites, camera lost masks the camera, stale telemetry locks commands, rejected command shows its reason, and a detection burst remains bounded to 20 candidates.

- [ ] **Step 5: Final production smoke**

Run:

```bash
npm run test:run
npx tsc --noEmit
npm run build
```

Expected: unit suite, typecheck, and production build pass. Chrome DevTools console remains free of hydration/runtime errors while confirm detection and RTL confirmation are exercised once.

## Self-Review

- **Spec coverage:** Tasks cover Carbon taste system, video-first layout, mock adapter, normalized detection overlay, mini-map, mission progress, limited controls, hold safety, RTL confirmation, failure alerts, target resolutions, and backend-replaceable contracts.
- **Scope:** WebRTC implementation, YOLO inference, MAVLink, and Pixhawk commands remain explicitly outside this frontend plan. They receive separate plans after frontend approval.
- **Completeness scan:** No incomplete implementation markers or unspecified test requests remain.
- **Type consistency:** `FlightState`, `FlightEvent`, `DetectionStatus`, `CommandType`, `FlightAdapter`, and component props use the same names across all tasks.
- **Taste check:** Carbon is the only design system; g100 is the only theme; cyan is interactive accent; semantic colors are status-only; one Carbon icon family; no decorative gradients, glass, pills, emojis, or motion.
