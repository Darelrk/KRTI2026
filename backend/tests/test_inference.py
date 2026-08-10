from types import SimpleNamespace

import pytest

from backend.app.inference import Detection, RTSPInference




class FakeSource:
    def __init__(self, frame: object | None) -> None:
        self.frame = frame
        self.closed = False

    def read(self) -> tuple[bool, object | None]:
        if self.frame is None:
            return False, None
        frame, self.frame = self.frame, None
        return True, frame

    def close(self) -> None:
        self.closed = True


class FakeDetector:
    def __init__(self, detections: list[Detection]) -> None:
        self.detections = detections

    def detect(self, frame: object, confidence: float) -> list[Detection]:
        return self.detections


def test_inference_emits_normalized_person_boxes_and_filters_other_classes():
    pipeline = RTSPInference(
        source=FakeSource(SimpleNamespace(shape=(100, 200, 3))),
        detector=FakeDetector(
            [
                Detection(x1=20, y1=10, x2=80, y2=60, confidence=0.91, class_name="person"),
                Detection(x1=0, y1=0, x2=10, y2=10, confidence=0.99, class_name="car"),
            ]
        ),
        clock=lambda: 1.0,
    )
    events = pipeline.run_once()
    assert len(events) == 1
    assert events[0].className == "person"
    assert events[0].box is not None
    assert events[0].box.x == 0.1
    assert events[0].box.y == 0.1
    assert events[0].box.width == pytest.approx(0.3)
    assert events[0].box.height == pytest.approx(0.5)
    assert events[0].frameId == 1


def test_inference_marks_source_disconnected_when_frame_read_fails():
    pipeline = RTSPInference(
        source=FakeSource(None),
        detector=FakeDetector([]),
        clock=lambda: 1.0,
    )
    assert pipeline.run_once() == []
    assert pipeline.health_state == "disconnected"


def test_inference_marks_source_stale_after_a_previous_frame():
    pipeline = RTSPInference(
        source=FakeSource(SimpleNamespace(shape=(100, 200, 3))),
        detector=FakeDetector([]),
    )
    assert pipeline.run_once() == []
    assert pipeline.health_state == "ready"
    assert pipeline.run_once() == []
    assert pipeline.health_state == "stale"


def test_close_releases_source():
    source = FakeSource(None)
    pipeline = RTSPInference(source=source, detector=FakeDetector([]))
    pipeline.close()
    assert source.closed is True
