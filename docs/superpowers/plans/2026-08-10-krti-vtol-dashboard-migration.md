# KRTI 2026 VTOL Dashboard Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mengubah dashboard UAV yang masih person/GPS/RTL-centric menjadi ground-station VTOL KRTI 2026 dengan misi 1-5, GPS map mengikuti pola dashboard KKI, telemetry posisi lengkap, vision targets, person safety warning, payload, retry, dan ELS.

**Architecture:** Pertahankan TanStack Start, TanStack Query, React reducer, Carbon `g100`, dan adapter boundary yang ada. Lakukan clean cutover pada kontrak event lalu port pola Google satellite iframe + SVG overlay + proyeksi local/GPS dari `D:/KKI2/KKI2026/dashboard`; backend tetap satu-satunya pihak yang berwenang mengirim MAVLink.

**Tech Stack:** TanStack Start, React 19, TypeScript, TanStack Query, IBM Carbon React/Icons, Sass, Vitest, Testing Library, Google Maps satellite embed.

**Source Spec:** `docs/superpowers/specs/2026-08-10-krti-vtol-dashboard-design.md`

**Repository Note:** `D:/KRTI` bukan repository Git. Langkah commit sengaja tidak dicantumkan; jangan membuat repository hanya untuk menjalankan rencana ini.

---

## File Structure

**Create**

- `frontend/src/domain/mission-map.ts` — tipe site, transformasi local/GPS, overlay calibration, dan URL satellite map.
- `frontend/src/test/mission-map.test.ts` — invariant round-trip, heading, calibration, dan URL map.
- `frontend/src/components/NavigationMap.tsx` — satellite iframe, SVG route/track, heading marker, coordinate readout, dan fallback grid.
- `frontend/src/test/navigation-map.test.tsx` — render map, no-fix, refresh, dan fallback.
- `frontend/src/components/PositionTelemetry.tsx` — latitude/longitude dan telemetry posisi/attitude.
- `frontend/src/components/PayloadStatus.tsx` — state paket medis.
- `frontend/src/components/SafetyEventQueue.tsx` — person/obstacle/link safety events dan acknowledgment UI.
- `frontend/src/test/vtol-sidebar.test.tsx` — progres, skor, position, payload, dan safety queue.
- `frontend/src/test/route-safety.test.ts` — command gating tanpa ketergantungan GPS.

**Modify**

- `frontend/src/domain/flight.ts` — ganti kontrak detection/waypoint/command lama dengan event VTOL.
- `frontend/src/domain/flight-reducer.ts` — state mission, payload, safety, track, vision targets, dan acknowledgment.
- `frontend/src/test/flight-reducer.test.ts` — kontrak reducer VTOL.
- `frontend/src/data/mock-flight-adapter.ts` — tiga belas skenario mock VTOL.
- `frontend/src/test/mock-flight-adapter.test.ts` — telemetry lengkap, vision, ELS, payload, dan command.
- `frontend/src/hooks/use-flight-session.ts` — acknowledgment safety dan derived stale/link-loss state.
- `frontend/src/components/VideoViewport.tsx` — camera identity dan vision targets.
- `frontend/src/components/MissionProgress.tsx` — lima fase, skor, timer, dan retry checkpoint.
- `frontend/src/components/StatusRail.tsx` — status VTOL dan telemetry kritis.
- `frontend/src/test/status-rail.test.tsx` — mode/altitude/range/time/no-data.
- `frontend/src/components/CriticalAlert.tsx` — person, collision, link-loss/ELS, camera, battery.
- `frontend/src/test/critical-alert.test.tsx` — prioritas alert VTOL.
- `frontend/src/components/CommandRail.tsx` — ARM, AUTO, HOLD, RETRY, EMERGENCY LAND.
- `frontend/src/test/command-rail.test.tsx` — hold/ack/retry/safety gating tanpa RTL/takeoff.
- `frontend/src/routes/index.tsx` — komposisi sidebar VTOL dan command gating non-GPS.
- `frontend/src/styles/app.scss` — layout map/sidebar/vision/safety/commands.
- `frontend/package.json` dan `frontend/package-lock.json` — hapus `maplibre-gl`.
**Rename**

- `frontend/src/components/DetectionOverlay.tsx` → `frontend/src/components/VisionOverlay.tsx`.
- `frontend/src/test/detection-overlay.test.tsx` → `frontend/src/test/vision-overlay.test.tsx`.


**Remove after replacement**

- `frontend/src/components/MiniMap.tsx` — digantikan `NavigationMap.tsx`.
- `frontend/src/components/DetectionQueue.tsx` — digantikan `SafetyEventQueue.tsx`.
- `frontend/src/test/detection-queue.test.tsx` — kontrak confirm/dismiss lama tidak berlaku.

---

### Task 1: Replace the Domain Contract with VTOL Events

**Files:**
- Modify: `frontend/src/domain/flight.ts`
- Modify: `frontend/src/domain/flight-reducer.ts`
- Modify: `frontend/src/test/flight-reducer.test.ts`

- [ ] **Step 1: Write reducer tests for the observable VTOL state**

Replace the old person-confirm/waypoint-only assertions with tests that prove:

```ts
const telemetry: TelemetryEvent = {
  type: 'telemetry', seq: 1, timestampMs: 1_000,
  armed: true, mode: 'AUTO', batteryPercent: 72, voltage: 15.9,
  latitude: -7.7706, longitude: 110.3776,
  gpsFix: 3, gpsSatellites: 12, hdop: 0.8,
  localXM: 12.5, localYM: 8.25,
  altitudeM: 6.4, rangefinderM: 5.9,
  groundSpeedMps: 2.3, headingDeg: 91,
  rollDeg: 1.2, pitchDeg: -0.7, yawDeg: 91,
  collisionClearanceM: 3.8,
}

expect(reduceFlightEvent(initialFlightState, telemetry).telemetry).toEqual(telemetry)
expect(reduceFlightEvent(initialFlightState, telemetry).track).toEqual([
  { latitude: -7.7706, longitude: 110.3776 },
])
```

Add separate tests for mission phase/score/retry checkpoint, payload state, person warning acknowledgment, ELS active, `box`/`path` vision geometry, and a track capped at 121 points.

- [ ] **Step 2: Run the reducer test and verify RED**

Run:

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/flight-reducer.test.ts
```

Expected: FAIL because `TelemetryEvent`, mission state, payload, safety, vision, and track still use the old contract.

- [ ] **Step 3: Replace `flight.ts` with the approved VTOL types**

Define the exact unions from the spec:

```ts
export type FlightMode = 'MANUAL' | 'AUTO' | 'HOLD' | 'ELS'
export type CameraId = 'front' | 'down'
export type VisionClass =
  | 'person' | 'aruco' | 'gate' | 'drop_zone' | 'line' | 'landing_pad'
export type CommandType =
  | 'arm' | 'enable_autonomy' | 'pause_mission' | 'retry' | 'emergency_land'
export type PayloadState = 'secured' | 'armed' | 'released' | 'unknown'
export type ElsState = 'standby' | 'countdown' | 'active'
export type MissionStatus = 'ready' | 'active' | 'passed' | 'failed' | 'retry'
export type RetryCheckpoint = 'START' | 'WP1' | 'WP2' | 'WP4'
```

Define these state shapes in the same file so later components share one vocabulary:

```ts
export type MissionState = {
  phase: 1 | 2 | 3 | 4 | 5
  phaseName: string
  waypointLabel: string
  status: MissionStatus
  elapsedSeconds: number
  score: number
  retryCheckpoint: RetryCheckpoint
  autonomyReady: boolean
}

export type SafetyState = {
  linkLostSeconds: number
  elsState: ElsState
  personWarning: boolean
  personAcknowledged: boolean
  obstacleWarning: boolean
}

export type VisionTarget = Omit<VisionEvent, 'type' | 'seq'>
export type MapEvent = {
  type: 'map'
  seq: number
  timestampMs: number
  baseAvailable: boolean
}
```

Use nullable `latitude`, `longitude`, `hdop`, `localXM`, `localYM`, `rangefinderM`, and `collisionClearanceM`. `VisionEvent` accepts optional `box` and `path`, with normalized coordinates. Include `MapEvent` in `FlightEvent`. Keep `FlightAdapter`, `CommandRequest`, and `CommandResult` names so the adapter boundary does not fork.

- [ ] **Step 4: Implement the minimal reducer state**

Use one state object:

```ts
export type FlightState = {
  telemetry: TelemetryEvent | null
  track: Array<{ latitude: number; longitude: number }>
  link: LinkState
  camera: { id: CameraId; connected: boolean; latencyMs: number; fps: number }
  map: { baseAvailable: boolean }
  mission: MissionState
  payload: PayloadState
  safety: SafetyState
  visionTargets: VisionTarget[]
  lastEventAt: number
}
```

Reducer invariants:

- append track only when both GPS values are non-null;
- cap track with `.slice(-121)`;
- update `map.baseAvailable` only from a `map` event;
- replace mission/payload/safety snapshots atomically;
- prepend vision targets and cap at 20;
- `ack_person_warning` sets `safety.personAcknowledged=true` without clearing the backend-owned `personWarning`;
- `trim_vision` keeps the newest 20 targets.

- [ ] **Step 5: Run the reducer test and verify GREEN**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/flight-reducer.test.ts
```

Expected: `1 file passed`, with all reducer tests passing.

---

### Task 2: Port the KKI GPS/Local Projection

**Files:**
- Create: `frontend/src/domain/mission-map.ts`
- Create: `frontend/src/test/mission-map.test.ts`

- [ ] **Step 1: Write projection tests**

Cover these contracts:

```ts
const site: MissionSite = {
  name: 'Mock VTOL site',
  center: { latitude: -7.7706, longitude: 110.3776 },
  courseReference: { x: 50, y: 50 },
  metersPerUnit: { x: 0.8, y: 0.6 },
  courseUpBearingDeg: 20,
}

const point = { x: 64, y: 37 }
expect(geoPointToCourse(coursePointToGeo(point, site), site).x)
  .toBeCloseTo(point.x, 6)
expect(geoPointToCourse(coursePointToGeo(point, site), site).y)
  .toBeCloseTo(point.y, 6)
```

Also assert:

- course reference maps exactly to site center;
- transformed north/south headings remain 180° apart;
- invalid latitude/longitude and zero scale throw `RangeError`;
- satellite URL uses `maps.google.com/maps`, `ll`, `z=22`, `t=k`, `output=embed`, and no `q`.

- [ ] **Step 2: Run projection tests and verify RED**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/mission-map.test.ts
```

Expected: FAIL because `mission-map.ts` does not exist.

- [ ] **Step 3: Implement the projection module using the KKI formulas**

Export:

```ts
export const EARTH_RADIUS_METERS = 6_371_008.8
export function coursePointToGeo(point: CoursePoint, site: MissionSite): GeoCoordinate
export function geoPointToCourse(point: GeoCoordinate, site: MissionSite): CoursePoint
export function coursePointToOverlay(point: CoursePoint, calibration: OverlayCalibration): OverlayPoint
export function courseHeadingToOverlay(headingDeg: number, calibration: OverlayCalibration): number
export function buildGoogleMapsSatelliteEmbedUrl(center: GeoCoordinate, zoom = 22): string
```

Use the same East/North rotation and heading transform as:

- `D:/KKI2/KKI2026/dashboard/src/lib/mission-site.ts`
- `D:/KKI2/KKI2026/dashboard/src/lib/site-map-projection.ts`

Do not import KKI source files across projects. Copy the small pure-math pattern and rename ASV-specific identifiers to generic VTOL names.

- [ ] **Step 4: Run projection tests and verify GREEN**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/mission-map.test.ts
```

Expected: all projection tests pass without DOM or network access.

---

### Task 3: Replace MapLibre MiniMap with the KKI-Style Navigation Map

**Files:**
- Create: `frontend/src/components/NavigationMap.tsx`
- Create: `frontend/src/test/navigation-map.test.tsx`
- Remove: `frontend/src/components/MiniMap.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

- [ ] **Step 1: Write component tests**

Render a map with a configured mock site and telemetry. Assert:

```ts
expect(screen.getByTitle('VTOL satellite base map')).toHaveAttribute(
  'src', expect.stringContaining('maps.google.com/maps'),
)
expect(screen.getByLabelText('VTOL position marker')).toHaveAttribute(
  'data-heading', '91',
)
expect(screen.getByText(/7\.770600° S/)).toBeVisible()
expect(screen.getByText(/110\.377600° E/)).toBeVisible()
```

Add tests that:

- no GPS renders `WAITING FOR GPS FIX` while keeping mission route visible;
- refresh changes the iframe key and recenters to latest telemetry;
- a `baseMapAvailable={false}` render shows `SATELLITE MAP UNAVAILABLE` and keeps the SVG overlay.

- [ ] **Step 2: Run the map component test and verify RED**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/navigation-map.test.tsx
```

Expected: FAIL because `NavigationMap.tsx` does not exist.

- [ ] **Step 3: Implement `NavigationMap`**

Use this public boundary:

```ts
type RouteMarker = {
  id: string
  kind: 'start' | 'waypoint' | 'gate' | 'drop_zone' | 'landing_pad'
  point: CoursePoint
}

type NavigationMapProps = {
  telemetry: TelemetryEvent | null
  track: FlightState['track']
  mission: FlightState['mission']
  site: MissionSite
  route: RouteMarker[]
  calibration: OverlayCalibration
  baseMapAvailable: boolean
}
```

Render:

- Google satellite iframe with `tabIndex={-1}`;
- neutral grid fallback under the overlay;
- north arrow;
- SVG route and travelled track;
- Start/WP/gate/drop/landing markers from the route model;
- VTOL marker rotated by transformed heading;
- six-decimal latitude/longitude readout;
- refresh button.

Use `telemetry.latitude/longitude`, then the last track point, then `site.center` as center priority. Show the waiting state when no real GPS exists even though the fallback center renders the map.

- [ ] **Step 4: Remove MapLibre cleanly**

Run:

```bash
cd D:/KRTI/frontend && npm uninstall maplibre-gl
```

Delete `MiniMap.tsx`; do not leave a compatibility re-export. Confirm no `maplibre` import remains:

```bash
cd D:/KRTI/frontend && npm ls maplibre-gl --depth=0
```

Expected: `(empty)` and exit code 1 from `npm ls`.

- [ ] **Step 5: Run the map tests and verify GREEN**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/mission-map.test.ts src/test/navigation-map.test.tsx
```

Expected: both map test files pass.

---

### Task 4: Rebuild the Mock Adapter Around VTOL Scenarios

**Files:**
- Modify: `frontend/src/data/mock-flight-adapter.ts`
- Modify: `frontend/src/test/mock-flight-adapter.test.ts`
- Modify: `frontend/src/hooks/use-flight-session.ts`

- [ ] **Step 1: Write failing adapter tests**

Test exact events for:

- normal Manual telemetry with complete position fields;
- `person-warning` emits `vision(person)` and `safety.personWarning=true`;
- `gps-no-fix` emits null global position but valid local X/Y;
- `els-active` emits `linkLostSeconds: 16`, `elsState: 'active'`, and mode `ELS`;
- `payload-released` emits payload `released`;
- `command-rejected` returns the backend reason;
- `enable_autonomy` is accepted only when mission phase 1 is ready/passed;
- no command result is fabricated before `sendCommand` resolves.

- [ ] **Step 2: Run adapter tests and verify RED**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/mock-flight-adapter.test.ts
```

Expected: FAIL because the adapter still emits `detection`, eight old scenarios, STABILIZE, and waypoint counts.

- [ ] **Step 3: Implement the thirteen approved scenario names**

Use:

```ts
export type MockScenario =
  | 'normal' | 'auto-transition' | 'person-warning' | 'vision-targets'
  | 'payload-released' | 'retry' | 'low-battery' | 'gps-no-fix'
  | 'map-unavailable' | 'camera-lost' | 'els-active'
  | 'collision-warning' | 'command-rejected'
```

Emit deterministic snapshot events before the 200 ms timer. Use one `publishVision(className, geometry)` helper and one complete telemetry factory. The `map-unavailable` scenario emits `MapEvent { baseAvailable: false }`; every other scenario emits `true`. Keep the existing `?scenario=` selection contract.

- [ ] **Step 4: Update `useFlightSession`**

Expose:

```ts
return {
  state: liveState,
  command,
  acknowledgePersonWarning: () => dispatch({ type: 'ack_person_warning' }),
}
```

Derived stale state may change `link` to `stale`, but must not synthesize `ELS ACTIVE`; ELS is accepted only from backend/mock safety events.

- [ ] **Step 5: Run adapter and reducer tests and verify GREEN**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/mock-flight-adapter.test.ts src/test/flight-reducer.test.ts
```

Expected: both files pass.

---

### Task 5: Generalize the Camera Overlay and Person Safety Warning

**Files:**
- Rename: `frontend/src/components/DetectionOverlay.tsx` → `frontend/src/components/VisionOverlay.tsx`
- Modify: `frontend/src/components/VideoViewport.tsx`
- Rename: `frontend/src/test/detection-overlay.test.tsx` → `frontend/src/test/vision-overlay.test.tsx`
- Create: `frontend/src/components/SafetyEventQueue.tsx`

- [ ] **Step 1: Write failing overlay tests**

Assert that:

```ts
expect(screen.getByText('PERSON 91%')).toBeVisible()
expect(screen.getByText('ARUCO 96% · ID 17')).toBeVisible()
expect(screen.getByLabelText('Detected mission line')).toHaveAttribute(
  'points', '192,864 960,540 1728,216',
)
```

Verify front-camera overlay excludes down-camera targets and person geometry receives a critical class distinct from mission targets.

- [ ] **Step 2: Run overlay tests and verify RED**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/vision-overlay.test.tsx
```

Expected: FAIL because the current component hardcodes `PERSON` and rectangles.

- [ ] **Step 3: Implement the generalized overlay**

Keep the 1920×1080 viewBox. For each target:

- render `<rect>` when `box` exists;
- render `<polyline>` when `path` exists;
- include marker ID only for ArUco;
- apply `vision-target--person` for red safety styling;
- apply target-specific text labels;
- render only targets for the active camera.

Rename the file and exported component to `VisionOverlay` using LSP file rename so imports move together; do not leave the old filename or export alias.

- [ ] **Step 4: Implement `SafetyEventQueue`**

The queue shows person, collision, link/ELS, and sensor warnings. Person acknowledgment invokes one callback and changes only UI acknowledgment state. It never calls `onCommand`.

- [ ] **Step 5: Run overlay tests and verify GREEN**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/vision-overlay.test.tsx
```

Expected: all box/path/camera/label assertions pass.

---

### Task 6: Build the VTOL Mission Sidebar and Position Readout

**Files:**
- Modify: `frontend/src/components/MissionProgress.tsx`
- Create: `frontend/src/components/PositionTelemetry.tsx`
- Create: `frontend/src/components/PayloadStatus.tsx`
- Create: `frontend/src/test/vtol-sidebar.test.tsx`
- Remove: `frontend/src/components/DetectionQueue.tsx`
- Remove: `frontend/src/test/detection-queue.test.tsx`

- [ ] **Step 1: Write sidebar tests**

Assert the five score rows `10, 40, 20, 15, 15`, remaining time from a 600-second mission, retry checkpoint, payload state, and exact telemetry formatting:

```ts
expect(screen.getByText('LAT -7.770600')).toBeVisible()
expect(screen.getByText('LON 110.377600')).toBeVisible()
expect(screen.getByText('LOCAL X 12.50 m')).toBeVisible()
expect(screen.getByText('HDG 091°')).toBeVisible()
expect(screen.getByText('ROLL +1.2°')).toBeVisible()
```

Render null GPS/local/range values and assert `NO FIX`/`NO DATA`, never `0.000000`.

- [ ] **Step 2: Run sidebar tests and verify RED**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/vtol-sidebar.test.tsx
```

Expected: FAIL because the current sidebar only supports waypoint count and person confirm/dismiss.

- [ ] **Step 3: Implement mission progress**

Render five fixed mission names and scores, but use backend `waypointLabel` verbatim to avoid resolving the guide's WP3/WP4 contradiction in the browser. The timer displays `10:00 - elapsedSeconds`, clamped at zero. Retry state displays `RETRY → <checkpoint>`.

- [ ] **Step 4: Implement position and payload components**

`PositionTelemetry` formats global, local, altitude/range, speed/heading, and roll/pitch/yaw. `PayloadStatus` renders `SECURED`, `ARMED`, `RELEASED`, or `UNKNOWN` with icon and text.

- [ ] **Step 5: Remove the obsolete detection queue**

Delete the component and its old test. Person safety acknowledgment is now exclusively owned by `SafetyEventQueue`.

- [ ] **Step 6: Run sidebar tests and verify GREEN**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/vtol-sidebar.test.tsx
```

Expected: all mission, score, timer, position, no-data, and payload assertions pass.

---

### Task 7: Replace Status, Alerts, and Commands with VTOL Safety Semantics

**Files:**
- Modify: `frontend/src/components/StatusRail.tsx`
- Modify: `frontend/src/test/status-rail.test.tsx`
- Modify: `frontend/src/components/CriticalAlert.tsx`
- Modify: `frontend/src/test/critical-alert.test.tsx`
- Modify: `frontend/src/components/CommandRail.tsx`
- Modify: `frontend/src/test/command-rail.test.tsx`

- [ ] **Step 1: Write failing status and alert tests**

Assert `KRTI VTOL`, `AUTO`, altitude/range, battery, remaining time, and visible `NO DATA`. Alert priority is:

1. ELS active;
2. disconnected/link-loss countdown;
3. collision warning;
4. person warning;
5. camera lost;
6. critical battery;
7. stale telemetry.

GPS no-fix must not produce a critical alert.

- [ ] **Step 2: Write failing command tests**

Assert:

- ARM requires 1.5-second hold;
- AUTO disabled until `autonomyReady`;
- RETRY shows destination checkpoint before sending;
- EMERGENCY LAND requires hold-to-confirm;
- result stays absent before the command promise resolves;
- no `RTL`, `Takeoff`, `Land`, or payload-drop button exists.

- [ ] **Step 3: Run the three component test files and verify RED**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/status-rail.test.tsx src/test/critical-alert.test.tsx src/test/command-rail.test.tsx
```

Expected: FAIL against the old UAV/GPS/RTL controls.

- [ ] **Step 4: Implement status and alert priority**

Status rail receives `FlightState` and renders link, mode, armed, altitude/range, battery, and mission timer. Critical alert returns the first matching alert in the priority list. ELS copy must say backend/flight-controller state, not imply the browser initiated it.

- [ ] **Step 5: Implement the command rail**

Use existing `useHoldAction` for ARM and EMERGENCY LAND. Use one confirmation state for retry destination. Buttons send only the five approved `CommandType` values. Keep accepted/rejected/unknown result rendering.

- [ ] **Step 6: Run the component tests and verify GREEN**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/status-rail.test.tsx src/test/critical-alert.test.tsx src/test/command-rail.test.tsx
```

Expected: all status, alert, and command contracts pass.

---

### Task 8: Integrate the VTOL Route and Carbon Layout

**Files:**
- Modify: `frontend/src/routes/index.tsx`
- Modify: `frontend/src/styles/app.scss`
- Create: `frontend/src/test/route-safety.test.ts`

- [ ] **Step 1: Write the route safety test**

Export this pure helper from `index.tsx`:

```ts
export function deriveCommandDisabled(input: {
  link: LinkState
  telemetryPresent: boolean
  commandPending: boolean
}) {
  return input.link !== 'connected' || !input.telemetryPresent || input.commandPending
}
```

The test proves the previous GPS gate is gone:

```ts
expect(deriveCommandDisabled({
  link: 'connected',
  telemetryPresent: true,
  commandPending: false,
})).toBe(false)
```

- [ ] **Step 2: Run the test and verify RED**

```bash
cd D:/KRTI/frontend && npm run test:run -- src/test/route-safety.test.ts
```

Expected: FAIL because `deriveCommandDisabled` does not exist and `index.tsx` still checks satellite count.

- [ ] **Step 3: Compose the approved sidebar**

Replace `MiniMap` and `DetectionQueue` imports with `NavigationMap`, `MissionProgress`, `PositionTelemetry`, `PayloadStatus`, and `SafetyEventQueue`. Pass `state.track`, `state.visionTargets`, mission/payload/safety state, and person acknowledgment from the hook.

Command gating is exactly:

```ts
const commandDisabled =
  state.link !== 'connected' || state.telemetry === null || command.isPending
```

Per-command readiness remains inside `CommandRail`; GPS satellite count is absent from this expression.

- [ ] **Step 4: Replace obsolete Sass selectors**

Delete `.mini-map`, `.detection-queue`, and old detection status selectors. Add focused rules for:

- `.navigation-map`, base iframe, neutral grid, wash, SVG overlay, route, track, markers, north arrow, coordinate readout;
- `.position-telemetry`, `.payload-status`, `.safety-event-queue`;
- `.vision-target--person` and mission-target geometry;
- five-column command rail;
- sidebar scroll containment at 1366×768.

Keep Carbon tokens and IBM Plex; do not add another styling system.

- [ ] **Step 5: Run all frontend tests and typecheck**

```bash
cd D:/KRTI/frontend && npm run test:run && npx tsc --noEmit
```

Expected: every Vitest file passes and TypeScript exits 0.

---

### Task 9: Production Build and Chrome DevTools Smoke Verification

**Files:**
- Modify only files implicated by an observed failure.

- [ ] **Step 1: Build the production bundle**

```bash
cd D:/KRTI/frontend && npm run build
```

Expected: Vite client and server builds exit 0; no MapLibre worker/font warning remains.

- [ ] **Step 2: Start the dashboard with the project process manager**

Start `npm run dev -- --host 127.0.0.1` on port 3000 through the harness process manager, not a background shell.

- [ ] **Step 3: Smoke the normal VTOL scenario through Chrome DevTools**

Open `http://127.0.0.1:3000/?scenario=normal` at 1366×768. Confirm:

- title/status says `KRTI VTOL`;
- camera dominates the main area;
- GPS satellite iframe and SVG route/marker appear;
- latitude/longitude and local/attitude values are visible;
- five mission rows and scores are visible;
- command rail contains ARM, AUTO, HOLD, RETRY, and EMERGENCY LAND;
- no horizontal overflow or console/page errors.

Repeat at 1920×1080.

- [ ] **Step 4: Smoke the safety scenarios**

Open these URLs and verify the stated contract:

- `?scenario=person-warning` — red person overlay and safety warning; no automatic command.
- `?scenario=gps-no-fix` — `NO FIX`, local X/Y still visible, commands not GPS-locked.
- `?scenario=map-unavailable` — neutral grid + SVG overlay, no blank panel.
- `?scenario=camera-lost` — `CAMERA LOST`, telemetry/map remain readable.
- `?scenario=els-active` — persistent `ELS ACTIVE` and emergency state.
- `?scenario=payload-released` — payload state reads `RELEASED`.

- [ ] **Step 5: Exercise command acknowledgment once**

Hold ARM for 1.5 seconds and confirm the UI changes only after `COMMAND ACCEPTED`. Open `?scenario=command-rejected`, send one allowed command, and confirm the backend reason is rendered.

- [ ] **Step 6: Run the final verification gate**

```bash
cd D:/KRTI/frontend && npm run test:run && npx tsc --noEmit && npm run build
```

Expected: all test files pass, TypeScript exits 0, and the production build exits 0.

Then run dependency absence separately:

```bash
cd D:/KRTI/frontend && npm ls maplibre-gl --depth=0
```

Expected: `(empty)` and exit code 1, proving the obsolete dependency is absent.
