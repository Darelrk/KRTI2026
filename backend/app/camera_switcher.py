from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from pathlib import Path
from time import time
from typing import Any

from .camera_selector import HardwareSwitcher
from .config import CameraProfile
from .contracts import CameraEvent, CameraId
from .event_bus import EventBus
from .inference import (
    FrameSource,
    OpenCVFrameSource,
    PersonDetector,
    RTSPInference,
    UltralyticsPersonDetector,
)
from .state_store import StateStore
from .video_ingest import LatestFrameBuffer


class CameraSwitchError(RuntimeError):
    pass


class CameraNotConfiguredError(CameraSwitchError):
    pass


SourceFactory = Callable[[str], FrameSource]
DetectorFactory = Callable[[str], PersonDetector]


def _default_source_factory(url: str) -> FrameSource:
    return LatestFrameBuffer(OpenCVFrameSource(url))


class CameraSwitcher:
    """Own one receiver stream and the detector for its logical camera."""

    def __init__(
        self,
        profiles: Mapping[CameraId, CameraProfile],
        store: StateStore,
        event_bus: EventBus,
        confidence: float = 0.25,
        source_factory: SourceFactory = _default_source_factory,
        detector_factory: DetectorFactory = UltralyticsPersonDetector,
        hardware_switcher: HardwareSwitcher | None = None,
    ) -> None:
        self._profiles = dict(profiles)
        self._store = store
        self._event_bus = event_bus
        self._confidence = confidence
        self._source_factory = source_factory
        self._detector_factory = detector_factory
        self._hardware_switcher = hardware_switcher
        self._lock = asyncio.Lock()
        self._active: RTSPInference | None = None
        self._active_camera: CameraId | None = None
        self.last_error: str | None = None

    @property
    def active_camera(self) -> CameraId | None:
        return self._active_camera

    @property
    def active_source(self) -> FrameSource:
        if self._active is None:
            raise RuntimeError("no camera is active")
        return self._active.source

    @property
    def active_model_path(self) -> Path | None:
        if self._active_camera is None:
            return None
        return self._profiles[self._active_camera].model_path

    @property
    def health_state(self) -> str:
        if self._active is None:
            return "degraded" if self.last_error else "disconnected"
        return self._active.health_state

    @property
    def profiles(self) -> Mapping[CameraId, CameraProfile]:
        return self._profiles

    async def start(self, camera: CameraId) -> dict[str, Any]:
        return await self.switch(camera)

    async def switch(self, camera: CameraId) -> dict[str, Any]:
        async with self._lock:
            profile = self._validate_profile(camera)
            if self._active_camera == camera and self._active is not None:
                return self._status_unlocked()

            old = self._active
            old_profile = (
                self._profiles.get(self._active_camera)
                if self._active_camera is not None
                else None
            )
            shared_stream = (
                old is not None
                and old_profile is not None
                and old_profile.video_url == profile.video_url
            )

            if shared_stream:
                return await self._switch_shared_stream(camera, profile, old)

            inference: RTSPInference | None = None
            try:
                inference = await asyncio.to_thread(self._build_inference, profile)
                start = getattr(inference.source, "start", None)
                if callable(start):
                    await asyncio.to_thread(start)
            except Exception as error:
                if inference is not None:
                    await asyncio.to_thread(inference.close)
                self.last_error = f"camera setup failed: {error}"
                raise CameraSwitchError(self.last_error) from error

            if old is not None:
                try:
                    await asyncio.to_thread(old.close)
                except Exception as error:
                    await asyncio.to_thread(inference.close)
                    self.last_error = f"failed to release camera: {error}"
                    raise CameraSwitchError(self.last_error) from error

            self._active = inference
            self._active_camera = camera
            self.last_error = None
            await self._publish_camera_state(camera, connected=True)
            return self._status_unlocked()

    async def publish_once(self) -> list[Any]:
        async with self._lock:
            if self._active is None:
                return []
            return await self._active.publish_once()

    async def close(self) -> None:
        async with self._lock:
            active = self._active
            self._active = None
            self._active_camera = None
            if active is not None:
                try:
                    await asyncio.to_thread(active.close)
                except Exception as error:
                    self.last_error = f"failed to close camera: {error}"

    def status(self) -> dict[str, Any]:
        return self._status_unlocked()

    def _status_unlocked(self) -> dict[str, Any]:
        return {
            "camera": self._active_camera,
            "active": self._active_camera,
            "hardwareSwitcherConfigured": self._hardware_switcher is not None,
            "cameras": {
                camera: {
                    "configured": bool(profile.video_url),
                    "active": camera == self._active_camera,
                    "stream": profile.video_url,
                    "model": str(profile.model_path),
                }
                for camera, profile in self._profiles.items()
            },
            "model": str(self.active_model_path) if self.active_model_path else None,
            "error": self.last_error,
        }

    async def _switch_shared_stream(
        self,
        camera: CameraId,
        profile: CameraProfile,
        active: RTSPInference,
    ) -> dict[str, Any]:
        if self._hardware_switcher is None:
            self.last_error = (
                "shared receiver stream requires a HardwareSwitcher adapter "
                "for physical camera selection"
            )
            raise CameraSwitchError(self.last_error)

        try:
            detector = await asyncio.to_thread(self._detector_factory, str(profile.model_path))
            await self._hardware_switcher.select(camera)
            clear = getattr(active.source, "clear", None)
            if callable(clear):
                clear()
        except Exception as error:
            self.last_error = f"hardware camera selection failed: {error}"
            raise CameraSwitchError(self.last_error) from error

        active.detector = detector
        active.camera = camera
        active.frame_id = 0
        active.health_state = "stale"
        active.last_error = None
        self._active_camera = camera
        self.last_error = None
        await self._publish_camera_state(camera, connected=True)
        return self._status_unlocked()

    def _validate_profile(self, camera: CameraId) -> CameraProfile:
        profile = self._profiles.get(camera)
        if profile is None or not profile.video_url:
            raise CameraNotConfiguredError(f"camera {camera!r} is not configured")
        if not profile.model_path.is_file():
            raise CameraSwitchError(f"model not found: {profile.model_path}")
        return profile

    def _build_inference(self, profile: CameraProfile) -> RTSPInference:
        assert profile.video_url is not None
        source = self._source_factory(profile.video_url)
        try:
            detector = self._detector_factory(str(profile.model_path))
            return RTSPInference(
                source=source,
                detector=detector,
                store=self._store,
                confidence=self._confidence,
                camera=profile.id,
            )
        except Exception:
            source.close()
            raise

    async def _publish_camera_state(self, camera: CameraId, connected: bool) -> None:
        event = await self._store.publish(
            CameraEvent(
                seq=0,
                timestampMs=max(0, int(time() * 1000)),
                id=camera,
                connected=connected,
                latencyMs=0,
                fps=0,
            )
        )
        await self._event_bus.publish(event)
