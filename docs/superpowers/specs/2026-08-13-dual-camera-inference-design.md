# Dual-Camera Inference Backend

## Goal

Support two regular cameras and one thermal/night camera connected through a transmitter that can run only one camera at a time. The backend must switch the active stream and matching detection model atomically.

## Existing constraints

- Current backend has one `VIDEO_URL`, one `MODEL_PATH`, one `RTSPInference`, and one `LatestFrameBuffer`.
- Existing physical camera IDs are `front` and `down`; add `night` without changing those regular IDs.
- Regular cameras use `model/best.pt`.
- Night/thermal camera uses `model/yolo26xthermal.pt`.
- EventBus is outbound-only for dashboard events; camera switching uses a REST endpoint rather than changing EventBus into a command bus.

## Configuration

Environment variables:

```env
FRONT_VIDEO_URL=rtsp://transmitter/front
DOWN_VIDEO_URL=rtsp://transmitter/down
NIGHT_VIDEO_URL=rtsp://transmitter/night
REGULAR_MODEL_PATH=model/best.pt
NIGHT_MODEL_PATH=model/yolo26xthermal.pt
ACTIVE_CAMERA=front
```

`Settings` parses a registry of three camera profiles. A profile contains an ID, stream URL, and model path. Missing URLs disable that profile. The active profile must have both a URL and an existing model before runtime starts it.

## Runtime design

`CameraSwitcher` owns the active `RTSPInference` and a registry of profile factories. It uses an `asyncio.Lock` for both camera switching and inference reads.

Switch sequence:

1. Acquire the switch lock.
2. Validate the requested profile and model path before closing the current source.
3. Close the old inference/source; release exceptions are captured and reported.
4. Construct the new detector and frame source lazily.
5. Start the new source.
6. Publish a camera state event and replace the active inference reference.
7. Release the lock.

No more than one `OpenCVFrameSource` is open. A failed switch leaves the old source closed and runtime health degraded; it never silently runs a model against the wrong camera.

The inference loop obtains the same lock while taking a frame and running detection, preventing a source/model swap during processing.

## HTTP contract

```http
POST /api/camera/switch
Content-Type: application/json

{"camera":"front"}
```

Valid IDs: `front`, `down`, `night`.

- `200`: switch accepted and active profile returned.
- `404`: profile is not configured.
- `409`: switch failed or profile could not be initialized.
- `422`: invalid camera ID.

`GET /api/cameras` returns configured profiles and active profile without exposing model internals beyond paths needed for diagnostics.

The existing `/api/health`, `/api/snapshot`, and `/ws/flight` contracts continue to work. Camera state reports the active physical/profile ID.

## Error handling

- Missing stream URL: reject before touching the active source.
- Missing model path: reject before touching the active source.
- Source release failure: continue cleanup, report the error, and do not start the replacement until cleanup completes.
- New source/model initialization failure: report degraded health and return a conflict response.
- Concurrent switch requests serialize through one lock.

## Testing

- Settings parses three profiles and model paths.
- Switches regular and night profiles with fake sources and fake detector factory.
- Verifies only one source is active and old sources are closed.
- Rejects missing profile/model before changing the active profile.
- Serializes concurrent switch calls.
- Existing inference normalization and runtime tests remain green.
