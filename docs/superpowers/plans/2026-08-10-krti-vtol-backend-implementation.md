# KRTI VTOL Backend Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun FastAPI bridge di laptop yang membaca Pixhawk melalui MAVLink serial, menerima RTSP/UDP, menjalankan inference lokal, dan menyediakan event/command backend untuk dashboard VTOL.

**Architecture:** Satu proses FastAPI modular dengan reader MAVLink, writer MAVLink tunggal, video/inference worker, in-memory state store, WebSocket event bus, REST command service, safety gate, dan reconnect manager. Serial dan video memiliki lifecycle terpisah; command penerbangan selalu fail-closed ketika serial atau heartbeat tidak sehat.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Pydantic, pymavlink, OpenCV, Ultralytics, pytest, pytest-asyncio, httpx, WebSocket TestClient.

**Source Spec:** `docs/superpowers/specs/2026-08-10-krti-vtol-backend-design.md`

**Repository note:** `D:/KRTI` bukan repository Git. Jangan membuat repository atau menambahkan langkah commit; setiap task diverifikasi dengan test/command yang tercantum.

---

## File Structure

**Create**

- `backend/requirements.txt` — runtime dependencies.
- `backend/requirements-dev.txt` — runtime plus test dependencies.
- `backend/app/__init__.py` — package marker.
- `backend/app/contracts.py` — Pydantic event, snapshot, health, and command models.
- `backend/app/config.py` — environment-backed validated settings.
- `backend/app/state_store.py` — in-memory snapshot and sequence state.
- `backend/app/event_bus.py` — async WebSocket subscriber queues.
- `backend/app/reconnect.py` — bounded reconnect/backoff policy.
- `backend/app/mavlink_reader.py` — MAVLink message mapping and serial reader protocol.
- `backend/app/mavlink_writer.py` — single-owner MAVLink command writer.
- `backend/app/safety.py` — command allowlist, preconditions, idempotency, and timeout policy.
- `backend/app/video_ingest.py` — RTSP/UDP frame source and latest-frame buffer.
- `backend/app/inference.py` — model adapter and normalized vision events.
- `backend/app/runtime.py` — lifecycle orchestration for serial, video, inference, and event publishing.
- `backend/app/main.py` — FastAPI app factory and routes.
- `backend/tests/conftest.py` — deterministic async/test settings and fake adapters.
- `backend/tests/test_config.py` — configuration validation.
- `backend/tests/test_contracts.py` — event shape and null handling.
- `backend/tests/test_state_store.py` — snapshots, sequence, and subscribers.
- `backend/tests/test_reconnect.py` — backoff and state transitions.
- `backend/tests/test_mavlink_reader.py` — fake MAVLink message mapping.
- `backend/tests/test_mavlink_writer.py` — serialized command writes and acknowledgment.
- `backend/tests/test_safety.py` — command gate behavior.
- `backend/tests/test_video_inference.py` — bounded frame buffer and normalized model output.
- `backend/tests/test_api.py` — health, snapshot, command, and WebSocket integration.
- `frontend/src/data/http-flight-adapter.ts` — browser adapter for the backend contract.
- `frontend/src/test/http-flight-adapter.test.ts` — HTTP/WebSocket adapter behavior.

**Modify**

- `frontend/src/hooks/use-flight-session.ts` — select HTTP/WebSocket adapter when backend URL is configured, retain mock adapter for local demo scenarios.
- `frontend/src/data/flight-adapter.ts` — keep the adapter boundary and document the backend-compatible methods if needed.
- `frontend/src/routes/index.tsx` — no location/site configuration; only consume telemetry/events from the selected adapter.
- `frontend/package.json` — no new dependency; use browser WebSocket and `fetch`.

---

### Task 1: Scaffold backend package, dependencies, settings, and contracts

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/contracts.py`
- Test: `backend/tests/test_config.py`
- Test: `backend/tests/test_contracts.py`

- [ ] **Step 1: Add the minimal runtime and test dependencies**

`backend/requirements.txt`:

```text
fastapi>=0.115,<1
uvicorn[standard]>=0.30,<1
pydantic>=2.8,<3
pymavlink>=2.4,<3
opencv-python>=4.10,<5
ultralytics>=8.3,<9
```

`backend/requirements-dev.txt`:

```text
-r requirements.txt
pytest>=8.3,<9
pytest-asyncio>=0.24,<1
httpx>=0.27,<1
```

- [ ] **Step 2: Write configuration tests first**

`backend/tests/test_config.py` must prove that defaults are local-only and invalid values fail:

```python
from pathlib import Path

import pytest

from backend.app.config import ConfigError, Settings


def test_defaults_are_local_and_use_repo_model():
    settings = Settings.from_env({})
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.pixhawk_baud == 115200
    assert settings.model_path == Path("model/best.pt")
    assert settings.cors_origins == ("http://127.0.0.1:3000",)


def test_serial_port_is_required_for_ready_runtime():
    settings = Settings.from_env({})
    assert settings.pixhawk_serial is None
    assert settings.serial_enabled is False


def test_invalid_numeric_settings_are_rejected():
    with pytest.raises(ConfigError, match="PIXHAWK_BAUD"):
        Settings.from_env({"PIXHAWK_BAUD": "not-a-number"})
```

- [ ] **Step 3: Define validated settings with no external settings package**

`backend/app/config.py` must expose `ConfigError` and `Settings.from_env(environ: Mapping[str, str])`. The fields are `host`, `port`, `pixhawk_serial: str | None`, `pixhawk_baud`, `video_url: str | None`, `model_path: Path`, `inference_conf`, `max_fps`, `serial_reconnect_max_seconds`, `command_timeout_seconds`, and `cors_origins: tuple[str, ...]`.

Parsing rules:

- blank serial/video values become `None`;
- `MODEL_PATH` defaults to `model/best.pt`;
- `CORS_ORIGINS` is comma-separated and never defaults to `*`;
- ports, baud, FPS, thresholds, and timeout values must be finite and positive where applicable;
- `HOST` defaults to `127.0.0.1`, never `0.0.0.0`;
- `serial_enabled` is true only when `pixhawk_serial` is set;
- `video_enabled` is true only when `video_url` is set.

- [ ] **Step 4: Define Pydantic contracts matching the frontend event vocabulary**

`backend/app/contracts.py` must define typed models for `TelemetryEvent`, `VisionEvent`, `MissionEvent`, `PayloadEvent`, `SafetyEvent`, `MapEvent`, `CameraEvent`, `LinkEvent`, `TrimVisionEvent`, `CommandRequest`, `CommandResult`, `FlightSnapshot`, and `HealthResponse`.

Use the same unions and nullable fields already present in `frontend/src/domain/flight.ts`. Keep every event field flat, include `type`, `seq`, and `timestampMs`, and use `model_config = ConfigDict(extra="forbid")` for commands and event payloads so misspelled fields fail early.

`CommandResult.status` is exactly `accepted | rejected | unknown`. `FlightEvent` is a discriminated union on `type`.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run from `D:/KRTI`:

```bash
python -m pytest backend/tests/test_config.py backend/tests/test_contracts.py -q
```

Expected: all configuration and contract tests pass.

---

### Task 2: Implement in-memory state store, event bus, and reconnect policy

**Files:**
- Create: `backend/app/state_store.py`
- Create: `backend/app/event_bus.py`
- Create: `backend/app/reconnect.py`
- Test: `backend/tests/test_state_store.py`
- Test: `backend/tests/test_reconnect.py`

- [ ] **Step 1: Write state and reconnect tests**

The tests must cover:

```python
async def test_store_increments_sequence_and_returns_latest_snapshot():
    store = StateStore(initial_snapshot=empty_snapshot())
    event = make_link_event("connected")
    await store.publish(event)
    assert (await store.snapshot()).link.state == "connected"
    assert event.seq == 1


def test_backoff_is_bounded():
    policy = ReconnectPolicy(max_seconds=30)
    assert [policy.delay_for(i) for i in range(6)] == [1, 2, 4, 8, 16, 30]
```

Also test subscriber queues receive events in order, slow subscribers are disconnected or bounded rather than allowing unbounded memory growth, and a new WebSocket subscriber receives the current snapshot events before incremental events.

- [ ] **Step 2: Implement `StateStore` with immutable replacement semantics**

Expose:

```python
class StateStore:
    async def publish(self, event: FlightEvent) -> FlightSnapshot:
        raise NotImplementedError

    async def snapshot(self) -> FlightSnapshot:
        raise NotImplementedError

    async def initial_events(self) -> list[FlightEvent]:
        raise NotImplementedError
```

The store keeps the latest telemetry, link, camera, map, mission, payload, safety, and at most 20 vision targets. GPS track is appended only when both coordinates are non-null and capped at 121 points. Every published event gets a strictly increasing `seq` if the source sequence is absent or stale. No event mutates a previously returned snapshot.

- [ ] **Step 3: Implement the bounded async event bus**

Expose `subscribe() -> AsyncIterator[FlightEvent]` and `publish(event)`. Each subscriber queue has a fixed size of 128. When full, discard the oldest non-safety vision event first; never silently discard telemetry, link, safety, mission, payload, or command acknowledgment events. If only critical events remain, close the subscriber with a clear overflow error.

- [ ] **Step 4: Implement reconnect policy as a pure function**

`ReconnectPolicy.delay_for(attempt: int) -> float` returns `min(2**attempt, max_seconds)` with the first delay equal to one second. Keep sleeping outside the policy so unit tests never wait in real time. Define explicit `DISCONNECTED`, `CONNECTING`, `READY`, and `STALE` string states.

- [ ] **Step 5: Run focused tests**

```bash
python -m pytest backend/tests/test_state_store.py backend/tests/test_reconnect.py -q
```

Expected: state, ordering, bounded queue, and backoff tests pass without real devices.

---

### Task 3: Implement MAVLink reader and telemetry mapping

**Files:**
- Create: `backend/app/mavlink_reader.py`
- Test: `backend/tests/test_mavlink_reader.py`

- [ ] **Step 1: Write fake-message mapping tests**

Define `Clock = Callable[[], float]` in `backend/app/mavlink_reader.py` and inject it into the reader so freshness tests use deterministic timestamps:

```python
from collections.abc import Callable

Clock = Callable[[], float]
```

Use `types.SimpleNamespace` fake messages and a fake clock. Prove that:

- `HEARTBEAT` maps custom mode and armed bit;
- `GLOBAL_POSITION_INT` maps latitude/longitude from `1e-7` degrees and altitude from millimeters;
- `GPS_RAW_INT` maps fix, satellite count, and HDOP when available;
- `ATTITUDE` converts radians to degrees;
- `SYS_STATUS` maps voltage and battery percent;
- `DISTANCE_SENSOR` maps rangefinder meters;
- `VFR_HUD` maps speed and heading;
- missing/invalid values become `None`;
- heartbeat age changes link to `stale` and then `disconnected` at explicit thresholds;
- a partial message updates only known telemetry fields rather than replacing valid fields with zero.
- [ ] **Step 2: Define reader protocols for real and fake transports**

Expose:

```python
class MavlinkTransport(Protocol):
    def recv_match(self, *, blocking: bool, timeout: float):
        raise NotImplementedError

    def send(self, message: object) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class MavlinkReader:
    def __init__(self, transport: MavlinkTransport, store: StateStore, clock: Clock):
        raise NotImplementedError

    def consume_message(self, message: object) -> list[FlightEvent]:
        raise NotImplementedError
```

Do not open a serial port inside the mapper. Keep conversion pure enough for tests and let a runtime factory create `pymavlink.mavutil.mavlink_connection(settings.pixhawk_serial, baud=settings.pixhawk_baud)`.

- [ ] **Step 3: Implement the mapping and freshness rules**

Use one telemetry accumulator per vehicle. Validate finite values, clamp only fields with protocol-defined ranges, and preserve `None` when a source is unavailable. Publish a `link` event when freshness crosses `connected`, `stale`, or `disconnected`. Publish telemetry at the configured cadence without blocking on WebSocket clients.

- [ ] **Step 4: Run focused tests**

```bash
python -m pytest backend/tests/test_mavlink_reader.py -q
```

Expected: all fake-message mapping and freshness tests pass without a COM port.

---

### Task 4: Implement the single MAVLink writer and safety gate

**Files:**
- Create: `backend/app/mavlink_writer.py`
- Create: `backend/app/safety.py`
- Test: `backend/tests/test_mavlink_writer.py`
- Test: `backend/tests/test_safety.py`

- [ ] **Step 1: Write safety-gate tests before implementation**

Cover these observable contracts:

```python
def test_rejects_commands_when_serial_is_not_ready():
    result = gate.evaluate(CommandRequest(commandId="a", type="arm"), state=disconnected_state())
    assert result.status == "rejected"
    assert result.reason == "Serial link is not ready"


def test_rejects_duplicate_command_id():
    gate.remember("a")
    result = gate.evaluate(CommandRequest(commandId="a", type="pause_mission"), state=ready_state())
    assert result.status == "rejected"
    assert result.reason == "Duplicate commandId"


def test_autonomy_requires_backend_readiness():
    result = gate.evaluate(CommandRequest(commandId="a", type="enable_autonomy"), state=ready_state(autonomy_ready=False))
    assert result.status == "rejected"
    assert result.reason == "Autonomy is not ready at the current checkpoint"
```

Also test allowlist rejection, stale heartbeat, command serialization, emergency land rejection when serial is unavailable, and no automatic retry after a timeout.

- [ ] **Step 2: Implement `SafetyGate` with explicit prerequisites**

Expose `evaluate(request, state) -> GateDecision`, `remember(command_id)`, and `clear_expired_ids()`. The gate must check allowlist, command idempotency, serial readiness, heartbeat freshness, mission preconditions, and one-flight-command-at-a-time. Use an in-memory bounded command-id cache with a finite expiry so it cannot grow without limit.

- [ ] **Step 3: Implement `MavlinkWriter` with one async lock**

Expose:

```python
class MavlinkWriter:
    async def execute(self, request: CommandRequest, state: FlightSnapshot) -> CommandResult:
        raise NotImplementedError
```

Translate only the five approved command types to explicit MAVLink operations. Await a matching acknowledgment up to `command_timeout_seconds`; return `unknown` on timeout. Never retry a flight command. The writer owns the transport lock and is the only code path allowed to call `transport.send`.

- [ ] **Step 4: Run focused tests**

```bash
python -m pytest backend/tests/test_safety.py backend/tests/test_mavlink_writer.py -q
```

Expected: gate, idempotency, serialization, acknowledgment, and timeout tests pass.

---

### Task 5: Implement RTSP/UDP ingest and local inference adapter

**Files:**
- Create: `backend/app/video_ingest.py`
- Create: `backend/app/inference.py`
- Test: `backend/tests/test_video_inference.py`

- [ ] **Step 1: Write fake-source and fake-model tests**

Test that:

- the frame buffer keeps only the latest bounded number of frames;
- a disconnected source reports `STALE` and does not emit live frames;
- fake model boxes convert pixel coordinates to normalized `x`, `y`, `width`, `height` in `0..1`;
- invalid boxes are dropped rather than published;
- results include source `frameId`, `camera`, confidence, and timestamp;
- inference skips stale frames and does not block the frame reader.

- [ ] **Step 2: Define source and model protocols**

Expose:

```python
class FrameSource(Protocol):
    def read(self) -> Frame | None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class Detector(Protocol):
    def detect(self, frame: Frame) -> list[VisionEvent]:
        raise NotImplementedError
```

`Frame` includes immutable image data, width, height, frame id, camera id, and capture timestamp. The production source uses `cv2.VideoCapture(settings.video_url)` and a one-frame/latest-frame handoff. The production detector loads `settings.model_path` once and filters to the configured vision classes.

- [ ] **Step 3: Implement normalized geometry conversion**

Use the image width and height to convert pixel coordinates. Clamp only small floating-point boundary drift into `0..1`; reject boxes with non-positive width/height or coordinates outside the image. Preserve frame id and capture timestamp through the conversion.

- [ ] **Step 4: Run focused tests**

```bash
python -m pytest backend/tests/test_video_inference.py -q
```

Expected: all fake source/model tests pass without opening RTSP or loading the real model.

---

### Task 6: Orchestrate workers and expose the FastAPI service

**Files:**
- Create: `backend/app/runtime.py`
- Create: `backend/app/main.py`
- Modify: `backend/app/__init__.py`
- Test: `backend/tests/test_api.py`
- Test: `backend/tests/conftest.py`

- [ ] **Step 1: Write API integration tests with injected fakes**

Use `create_app(settings, runtime)` so tests never open COM ports or RTSP. Cover:

The API test module must define these test cases:

- `test_health_reports_degraded_serial_without_hiding_video`;
- `test_snapshot_returns_frontend_compatible_state`;
- `test_command_is_rejected_before_serial_ready`;
- `test_command_returns_writer_result_when_gate_passes`;
- `test_websocket_sends_initial_events_then_incremental_event`.

The WebSocket test must assert event ordering and the presence of `type`, `seq`, and `timestampMs`.

- [ ] **Step 2: Implement `Runtime` lifecycle**

Expose `start()`, `stop()`, `health()`, `snapshot()`, `command(request)`, and `subscribe()`. Start serial and video tasks independently. Catch transport errors, publish health/link state, sleep through `ReconnectPolicy`, and retry. On shutdown, cancel tasks, close video, and close serial without leaving background threads.

- [ ] **Step 3: Implement the FastAPI app factory**

`create_app(settings: Settings | None = None, runtime: Runtime | None = None) -> FastAPI` must:

- configure CORS from explicit origins;
- use a lifespan context to start/stop runtime;
- expose `GET /api/health`;
- expose `GET /api/snapshot`;
- expose `POST /api/commands` with Pydantic validation;
- expose `WS /ws/flight` with initial event replay and incremental subscription;
- return structured HTTP 400/409/503 errors for malformed, duplicate, or unavailable commands;
- bind to `127.0.0.1` by default when launched by Uvicorn.

- [ ] **Step 4: Run API integration tests**

```bash
python -m pytest backend/tests/test_api.py -q
```

Expected: all HTTP and WebSocket tests pass with fake runtime components.

---

### Task 7: Connect the existing dashboard to the real backend adapter

**Files:**
- Create: `frontend/src/data/http-flight-adapter.ts`
- Create: `frontend/src/test/http-flight-adapter.test.ts`
- Modify: `frontend/src/hooks/use-flight-session.ts`
- Modify: `frontend/src/data/flight-adapter.ts` only if the shared interface needs a documented optional close method.

- [ ] **Step 1: Write browser adapter tests**

Test with mocked `fetch` and `WebSocket`:

- `getSnapshot()` calls `/api/snapshot` and returns the exact `FlightState` shape;
- `subscribe()` opens `ws://` for an `http://` backend URL and `wss://` for `https://`;
- each WebSocket message is parsed and forwarded to the reducer listener;
- WebSocket close invokes the unsubscribe cleanup and does not throw;
- `sendCommand()` posts JSON to `/api/commands` and returns the backend `CommandResult`;
- non-2xx responses become rejected promises with the response reason.

- [ ] **Step 2: Implement `HttpFlightAdapter` with browser-native APIs**

Constructor signature:

```ts
export class HttpFlightAdapter implements FlightAdapter {
  constructor(private readonly baseUrl: string) {}
  getSnapshot(): Promise<FlightState> { /* fetch /api/snapshot */ }
  subscribe(listener: (event: FlightEvent) => void): () => void { /* WebSocket */ }
  sendCommand(command: CommandRequest): Promise<CommandResult> { /* POST */ }
}
```

Do not add a WebSocket dependency. Normalize trailing slashes once and convert HTTP protocol to WebSocket protocol by URL parsing rather than string concatenation.

- [ ] **Step 3: Select the adapter without breaking mock scenarios**

In `use-flight-session.ts`, use `VITE_BACKEND_URL` when present and no `?scenario=` query parameter is selected. Keep the current mock adapter for the existing scenario-driven demo and tests. Ensure query snapshot errors are surfaced as link/degraded state rather than crashing the page.

- [ ] **Step 4: Run frontend adapter and existing tests**

```bash
cd D:/KRTI/frontend
npm run test:run -- src/test/http-flight-adapter.test.ts
npm run test:run
npx tsc --noEmit
```

Expected: new adapter tests and all existing VTOL tests pass.

---

### Task 8: Add local run configuration and hardware smoke checks

**Files:**
- Create: `backend/.env.example`
- Create: `backend/tests/test_smoke_contract.py`
- Modify: `docs/superpowers/specs/2026-08-10-krti-vtol-backend-design.md` only if implementation reveals a contract change.

- [ ] **Step 1: Add explicit local environment example**

`backend/.env.example` must contain safe local values:

```dotenv
HOST=127.0.0.1
PORT=8000
PIXHAWK_SERIAL=COM7
PIXHAWK_BAUD=115200
VIDEO_URL=rtsp://127.0.0.1:8554/uav
MODEL_PATH=model/best.pt
INFERENCE_CONF=0.25
MAX_FPS=10
SERIAL_RECONNECT_MAX_SECONDS=30
COMMAND_TIMEOUT_SECONDS=2
CORS_ORIGINS=http://127.0.0.1:3000
```

Do not include credentials or public bind addresses.

- [ ] **Step 2: Add a no-hardware smoke contract test**

The test starts `create_app` with fake runtime, requests health and snapshot, opens the WebSocket, publishes one telemetry event, and verifies the dashboard-compatible message. This is the deterministic check that remains runnable without Pixhawk or RTSP.

- [ ] **Step 3: Run the deterministic backend gate**

From `D:/KRTI`:

```bash
python -m pytest backend/tests -q
```

Expected: all backend tests pass without hardware.

- [ ] **Step 4: Run the real local service with configured devices**

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

With Pixhawk and RTSP configured, verify:

```text
GET http://127.0.0.1:8000/api/health -> serial/video/inference states
GET http://127.0.0.1:8000/api/snapshot -> current FlightState-compatible snapshot
WS  ws://127.0.0.1:8000/ws/flight -> initial and incremental events
```

Disconnect serial and video separately. Confirm reconnect attempts, stale/disconnected events, and command rejection while serial is unhealthy. Do not test ARM or emergency land on a live airframe without an approved safety window.

---

## Final Verification Gate

Run all deterministic checks:

```bash
cd D:/KRTI
python -m pytest backend/tests -q
cd frontend
npm run test:run
npx tsc --noEmit
npm run build
```

Then run the local FastAPI service and the frontend against `VITE_BACKEND_URL=http://127.0.0.1:8000`. Acceptance requires:

- no backend test failures;
- no frontend regression failures;
- WebSocket snapshot hydration works;
- telemetry continues while video reconnects;
- commands fail closed when serial/heartbeat is stale;
- no command is retried automatically;
- no location-specific map/site data is introduced;
- production frontend build succeeds.
