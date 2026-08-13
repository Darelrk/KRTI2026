# Dual-Camera Inference Backend

## Goal

Support two regular cameras and one thermal/night camera connected through a transmitter whose receiver exposes only one stream at a time. The backend switches the logical camera, physical transmitter selection, and matching detection model without opening duplicate receiver streams.

The physical selection mechanism is intentionally not assumed yet: the transmitter may later be controlled through a cable connected to Pixhawk and Hello Radio, a serial command, or another device-specific method.

## Existing constraints

- Current backend has one `VIDEO_URL`, one `MODEL_PATH`, one `RTSPInference`, and one `LatestFrameBuffer`.
- Existing physical camera IDs are `front` and `down`; add `night` without changing those regular IDs.
- Regular cameras use `model/best.pt`.
- Night/thermal camera uses `model/yolo26xthermal.pt`.
- EventBus is outbound-only for dashboard events; camera switching uses REST rather than changing EventBus into a command bus.
- The receiver must have at most one active frame source.

## Configuration

Environment variables:

```env
FRONT_VIDEO_URL=rtsp://transmitter/receiver
DOWN_VIDEO_URL=rtsp://transmitter/receiver
NIGHT_VIDEO_URL=rtsp://transmitter/receiver
REGULAR_MODEL_PATH=model/best.pt
NIGHT_MODEL_PATH=model/yolo26xthermal.pt
ACTIVE_CAMERA=front
```

If the receiver exposes different URLs, profiles may use different URLs. If all cameras share one receiver stream, use the same URL for each profile. `Settings` parses a registry of three camera profiles; missing URLs disable profiles.

`ACTIVE_CAMERA` identifies the logical camera expected at startup. Without a hardware adapter, startup can attach to the already-selected transmitter input, but a later switch between profiles sharing one URL fails closed instead of claiming that the physical camera changed.

## Hardware adapter boundary

`HardwareSwitcher` is the only contract required by `CameraSwitcher`:

```python
class HardwareSwitcher(Protocol):
    async def select(self, camera: CameraId) -> None: ...
```

The adapter receives only `front`, `down`, or `night`. It owns all COM-port discovery, baud rate, Pixhawk/Hello Radio protocol, relay/servo mapping, acknowledgements, and retries. The core backend does not guess a COM number or invent a control packet.

`build_runtime(settings, hardware_switcher=None)` accepts the adapter for future wiring. Until the transmitter protocol is known, the value remains `None` and shared-stream switching returns a clear conflict.

## Runtime design

`CameraSwitcher` owns the active `RTSPInference`, profile registry, and optional `HardwareSwitcher`. One `asyncio.Lock` serializes camera switching and inference reads.

Switch sequence:

1. Acquire the switch lock.
2. Validate the requested profile, stream URL, and model path before touching the active source.
3. If the current and target profiles share a stream URL, construct the target detector and call `HardwareSwitcher.select(camera)`. On failure, preserve the current camera, source, and detector.
4. For a shared stream success, keep the existing `LatestFrameBuffer`, replace only the detector and logical camera ID, and reset the frame counter.
5. For different stream URLs, construct and start the replacement source/model first; then close the old source and commit the replacement.
6. Publish a `CameraEvent` and expose the new logical camera through the status endpoint.

The shared-stream path never opens a second `OpenCVFrameSource`. The different-stream path keeps one active source after a successful switch. A failed switch never silently runs a model against a different logical camera.

## HTTP contract

```http
POST /api/cameras/switch
Content-Type: application/json

{"camera":"front"}
```

Valid IDs: `front`, `down`, `night`.

- `200`: switch accepted and active profile returned.
- `409`: profile is not configured, model/source setup failed, or a shared stream has no working hardware adapter.
- `422`: invalid camera ID.

`GET /api/cameras` returns configured profiles, active logical profile, model paths, stream identifiers, and whether a hardware adapter is configured. The response does not expose credentials.

The existing `/api/health`, `/api/snapshot`, and `/ws/flight` contracts continue to work. Camera state reports the active logical profile ID.

## Error handling

- Missing stream URL: reject before touching the active source.
- Missing model path: reject before touching the active source.
- Hardware selection failure: preserve the active source/model and return a conflict.
- Source release failure: close the replacement, report the error, and do not commit the replacement.
- New source/model initialization failure: preserve the active source and return a conflict.
- Concurrent switch requests serialize through one lock.

## Testing

- Settings parses three profiles and model paths.
- Different-stream switching closes the old source and uses the matching model.
- Shared-stream switching calls a fake hardware adapter and keeps one source.
- Shared-stream switching without an adapter fails closed and preserves the active source.
- Missing profile/model is rejected before changing the active profile.
- Concurrent switch calls serialize.
- Existing inference normalization and runtime tests remain green.
