from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable, Protocol

from .contracts import VisionEvent
from .state_store import StateStore


class FrameSource(Protocol):
    def read(self) -> tuple[bool, object | None]: ...

    def close(self) -> None: ...


class PersonDetector(Protocol):
    def detect(self, frame: object, confidence: float) -> list[Detection]: ...


@dataclass(frozen=True)
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str


class RTSPInference:
    def __init__(
        self,
        source: FrameSource,
        detector: PersonDetector,
        store: StateStore | None = None,
        confidence: float = 0.25,
        camera: str = "front",
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.source = source
        self.detector = detector
        self.store = store
        self.confidence = confidence
        self.camera = camera
        self.clock = clock
        self.frame_id = 0
        self.health_state = "disconnected"
        self.last_error: str | None = None

    def run_once(self) -> list[VisionEvent]:
        ok, frame = self.source.read()
        if not ok or frame is None:
            self.health_state = "stale" if self.frame_id else "disconnected"
            return []
        self.frame_id += 1
        try:
            detections = self.detector.detect(frame, self.confidence)
            width, height = self._frame_size(frame)
            events = [
                self._event(detection, width, height)
                for detection in detections
                if detection.class_name == "person"
                and detection.confidence >= self.confidence
            ]
            self.health_state = "ready"
            self.last_error = None
            return [event for event in events if event is not None]
        except Exception as error:
            self.health_state = "degraded"
            self.last_error = str(error)
            return []

    async def publish_once(self) -> list[VisionEvent]:
        events = await asyncio.to_thread(self.run_once)
        if self.store is not None:
            for event in events:
                await self.store.publish(event)
        return events

    async def run(self, stop: asyncio.Event, max_fps: float = 10.0) -> None:
        interval = 1.0 / max(0.1, max_fps)
        try:
            while not stop.is_set():
                started = monotonic()
                await self.publish_once()
                remaining = interval - (monotonic() - started)
                if remaining > 0:
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=remaining)
                    except asyncio.TimeoutError:
                        pass
        finally:
            self.close()

    def close(self) -> None:
        self.source.close()

    def _event(self, detection: Detection, width: int, height: int) -> VisionEvent | None:
        if width <= 0 or height <= 0:
            return None
        x1 = self._clip(detection.x1 / width)
        y1 = self._clip(detection.y1 / height)
        x2 = self._clip(detection.x2 / width)
        y2 = self._clip(detection.y2 / height)
        if x2 <= x1 or y2 <= y1:
            return None
        return VisionEvent(
            seq=self.frame_id,
            timestampMs=max(0, int(self.clock() * 1000)),
            id=f"{self.camera}-{self.frame_id}",
            frameId=self.frame_id,
            camera=self.camera,  # type: ignore[arg-type]
            className="person",
            confidence=min(1.0, max(0.0, detection.confidence)),
            box={"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
        )

    @staticmethod
    def _frame_size(frame: object) -> tuple[int, int]:
        shape = getattr(frame, "shape", None)
        if shape is None or len(shape) < 2:
            raise ValueError("frame has no image dimensions")
        return int(shape[1]), int(shape[0])

    @staticmethod
    def _clip(value: float) -> float:
        return min(1.0, max(0.0, float(value)))


class OpenCVFrameSource:
    def __init__(self, url: str) -> None:
        import cv2

        self.capture = cv2.VideoCapture(url)

    def read(self) -> tuple[bool, object | None]:
        return self.capture.read()

    def close(self) -> None:
        self.capture.release()


class UltralyticsPersonDetector:
    def __init__(self, model_path: str) -> None:
        from ultralytics import YOLO

        self.model = YOLO(model_path)

    def detect(self, frame: object, confidence: float) -> list[Detection]:
        result = self.model(frame, conf=confidence, verbose=False)[0]
        boxes = result.boxes
        names = result.names
        detections: list[Detection] = []
        for coordinates, score, class_id in zip(
            boxes.xyxy.cpu().tolist(),
            boxes.conf.cpu().tolist(),
            boxes.cls.cpu().tolist(),
        ):
            label = names[int(class_id)] if isinstance(names, list) else names[int(class_id)]
            detections.append(
                Detection(
                    x1=float(coordinates[0]),
                    y1=float(coordinates[1]),
                    x2=float(coordinates[2]),
                    y2=float(coordinates[3]),
                    confidence=float(score),
                    class_name=str(label),
                )
            )
        return detections
