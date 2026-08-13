# Dual-Camera Inference Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add atomic switching between front/down regular cameras using `model/best.pt` and a night/thermal camera using `model/yolo26xthermal.pt`, with only one active stream and detector.

**Architecture:** `Settings` exposes three camera profiles and separate regular/night model paths. A new `CameraSwitcher` owns the active `RTSPInference`, serializes switch and inference operations with `asyncio.Lock`, validates the target before closing the old source, and publishes the active camera through the existing outbound `EventBus`. Runtime routes `POST /api/camera/switch` and `GET /api/cameras`; the existing health, snapshot, and websocket paths remain intact.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, asyncio, OpenCV, Ultralytics, pytest.

---

### Task 1: Extend camera configuration and contracts

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/contracts.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_config.py`
- Test: `backend/tests/test_contracts.py`

- [ ] **Step 1: Write failing configuration tests**

Add tests asserting that `Settings.from_env` parses `FRONT_VIDEO_URL`, `DOWN_VIDEO_URL`, `NIGHT_VIDEO_URL`, `REGULAR_MODEL_PATH`, `NIGHT_MODEL_PATH`, and `ACTIVE_CAMERA`, and rejects an invalid active camera with `ConfigError`.

```python
def test_camera_profiles_are_parsed():
    settings = Settings.from_env({
        "FRONT_VIDEO_URL": " rtsp://front ",
        "DOWN_VIDEO_URL": "rtsp://down",
        "NIGHT_VIDEO_URL": "rtsp://night",
        "REGULAR_MODEL_PATH": "model/best.pt",
        "NIGHT_MODEL_PATH": "model/yolo26xthermal.pt",
        "ACTIVE_CAMERA": "night",
    })
    assert settings.camera_profiles["night"].video_url == "rtsp://night"
    assert settings.camera_profiles["front"].model_path == Path("model/best.pt")
    assert settings.active_camera == "night"


def test_invalid_active_camera_is_rejected():
    with pytest.raises(ConfigError, match="ACTIVE_CAMERA"):
        Settings.from_env({"ACTIVE_CAMERA": "side"})
```

Update contract tests to accept `night` as a valid `CameraEvent.id` and `VisionEvent.camera`.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
pytest backend/tests/test_config.py backend/tests/test_contracts.py -q
```

Expected: failures because the new profile fields and `night` camera literal do not exist.

- [ ] **Step 3: Implement the configuration and contract types**

Add `CameraId = Literal["front", "down", "night"]` and a frozen `CameraProfile` dataclass with `id`, `video_url`, and `model_path`. Add `front_video_url`, `down_video_url`, `night_video_url`, `regular_model_path`, `night_model_path`, and `active_camera` to `Settings`; expose a `camera_profiles` property returning the three profile objects. Parse the new env variables while retaining local-safe defaults of `None` for URLs and the existing model paths.

Add the following `.env.example` entries:

```env
FRONT_VIDEO_URL=rtsp://127.0.0.1:8554/front
DOWN_VIDEO_URL=rtsp://127.0.0.1:8554/down
NIGHT_VIDEO_URL=rtsp://127.0.0.1:8554/night
REGULAR_MODEL_PATH=model/best.pt
NIGHT_MODEL_PATH=model/yolo26xthermal.pt
ACTIVE_CAMERA=front
```

- [ ] **Step 4: Run the focused tests and verify pass**

Run:

```bash
pytest backend/tests/test_config.py backend/tests/test_contracts.py -q
```

Expected: all focused configuration and contract tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/contracts.py backend/.env.example backend/tests/test_config.py backend/tests/test_contracts.py
git commit -m "feat: add regular and night camera profiles"
```

### Task 2: Add the atomic CameraSwitcher

**Files:**
- Create: `backend/app/camera_switcher.py`
- Modify: `backend/app/inference.py`
- Test: `backend/tests/test_camera_switcher.py`

- [ ] **Step 1: Write failing switcher tests**

Create fake source and detector factories. Test that switching closes the old source before activating the new one, rejects a missing URL/model without touching the old source, and serializes concurrent switches.

```python
@pytest.mark.asyncio
async def test_switch_closes_old_source_and_uses_matching_model():
    switcher = make_switcher(front_url="front", night_url="night")
    await switcher.start()
    old = switcher.active_source
    result = await switcher.switch("night")
    assert result.camera == "night"
    assert old.closed is True
    assert switcher.active_model_path == Path("model/yolo26xthermal.pt")
    assert switcher.active_source is not old

@pytest.mark.asyncio
async def test_missing_model_is_rejected_before_closing_active_source(tmp_path):
    switcher = make_switcher(front_url="front", night_url="night", night_model=tmp_path / "missing.pt")
    await switcher.start()
    old = switcher.active_source
    with pytest.raises(CameraSwitchError, match="model"):
        await switcher.switch("night")
    assert old.closed is False
    assert switcher.active_camera == "front"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
pytest backend/tests/test_camera_switcher.py -q
```

Expected: collection failure because `CameraSwitcher` does not exist.

- [ ] **Step 3: Implement the switcher and detector factory seam**

Implement `CameraSwitcher` with:

- `asyncio.Lock` shared by `switch`, `publish_once`, and `close`;
- profile validation before old-source cleanup;
- `await asyncio.to_thread(old.close)` to avoid blocking the event loop;
- `OpenCVFrameSource` and `LatestFrameBuffer` creation only for the selected profile;
- `UltralyticsPersonDetector(str(profile.model_path))` through an injectable detector factory;
- source `start()` after the new inference object is completely constructed;
- cleanup of a partially constructed source if detector/source initialization fails;
- `active_camera`, `active_source`, `active_model_path`, `profiles`, and `last_error` read-only diagnostics;
- camera event publication through `StateStore.publish` followed by `EventBus.publish`.

Keep `RTSPInference` unchanged in its normalization behavior; only add a typed camera ID where required. Do not load all three models or open all three streams.

- [ ] **Step 4: Run focused switcher and inference tests**

Run:

```bash
pytest backend/tests/test_camera_switcher.py backend/tests/test_inference.py -q
```

Expected: all switcher and existing inference tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/camera_switcher.py backend/app/inference.py backend/tests/test_camera_switcher.py
git commit -m "feat: add atomic camera and model switching"
```

### Task 3: Integrate switching into Runtime and HTTP API

**Files:**
- Modify: `backend/app/runtime.py`
- Modify: `backend/app/contracts.py`
- Test: `backend/tests/test_api.py`
- Test: `backend/tests/test_runtime.py` (create if absent)

- [ ] **Step 1: Write failing API tests**

Add tests for `GET /api/cameras`, successful `POST /api/camera/switch`, invalid camera validation, and unconfigured camera rejection. Use the existing `create_app(runtime=...)` injection path with a fake `CameraSwitcher` or fake runtime method.

```python
def test_camera_switch_endpoint(client):
    response = client.post("/api/camera/switch", json={"camera": "night"})
    assert response.status_code == 200
    assert response.json()["camera"] == "night"


def test_camera_switch_rejects_invalid_id(client):
    response = client.post("/api/camera/switch", json={"camera": "side"})
    assert response.status_code == 422
```

- [ ] **Step 2: Run the focused API tests and verify failure**

Run:

```bash
pytest backend/tests/test_api.py -q
```

Expected: 404 for the new route or missing request model.

- [ ] **Step 3: Implement Runtime integration**

Add `CameraSwitchRequest` and a response shape containing the active camera and model path. Add `Runtime.switch_camera(camera_id)` and `Runtime.camera_status()` delegating to `CameraSwitcher`. Replace the single inference construction in `build_runtime` with a `CameraSwitcher` created from `Settings.camera_profiles` and the existing `StateStore`/`EventBus`.

Make `_inference_loop` call `await self.camera_switcher.publish_once()` while retaining serial loop behavior. `Runtime.health()` must report the switcher health/error. `Runtime.stop()` must close the switcher once.

Add:

```python
@app.get("/api/cameras")
async def cameras() -> dict[str, Any]:
    return runtime.camera_status()

@app.post("/api/camera/switch")
async def switch_camera(request: CameraSwitchRequest) -> dict[str, Any] | JSONResponse:
    try:
        return await runtime.switch_camera(request.camera)
    except CameraNotConfiguredError as error:
        return JSONResponse(status_code=404, content={"detail": str(error)})
    except CameraSwitchError as error:
        return JSONResponse(status_code=409, content={"detail": str(error)})
```

Do not change existing `/api/commands` behavior.

- [ ] **Step 4: Run API and runtime tests**

Run:

```bash
pytest backend/tests/test_api.py backend/tests/test_runtime.py -q
```

Expected: all new camera API tests pass and existing endpoint tests remain green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/runtime.py backend/app/contracts.py backend/tests/test_api.py backend/tests/test_runtime.py
git commit -m "feat: expose camera switching API"
```

### Task 4: Documentation and full verification

**Files:**
- Modify: `backend/.env.example`
- Modify: `backend/README.md` if present, otherwise `docs/superpowers/specs/2026-08-13-dual-camera-inference-design.md`

- [ ] **Step 1: Document launch and switching commands**

Document configuration and examples:

```bash
curl http://127.0.0.1:8000/api/cameras
curl -X POST http://127.0.0.1:8000/api/camera/switch -H "Content-Type: application/json" -d "{\"camera\":\"night\"}"
```

State explicitly that `model/yolo26xthermal.pt` is the night/thermal model and `model/best.pt` is the regular model.

- [ ] **Step 2: Run the complete backend verification**

Run:

```bash
pytest backend/tests -q
python -m compileall backend/app
```

Expected: all backend tests pass and compileall exits 0.

- [ ] **Step 3: Run a no-camera smoke test**

Run:

```bash
python -c "from backend.app.config import Settings; from backend.app.runtime import build_runtime; r=build_runtime(Settings.from_env({})); print(r.camera_status())"
```

Expected: no stream is opened, profiles are reported disabled, and the command exits 0.

- [ ] **Step 4: Audit repository state**

Run:

```bash
git diff --check
git status --short --branch
git log -3 --oneline --decorate
```

Expected: no whitespace errors; only intentional committed changes; branch is synchronized after push.
