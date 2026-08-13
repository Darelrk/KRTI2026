import time
from types import SimpleNamespace

from backend.app.video_ingest import LatestFrameBuffer


class ClosedSource:
    def __init__(self) -> None:
        self.closed = False

    def read(self) -> tuple[bool, object | None]:
        time.sleep(0.01)
        return False, None

    def close(self) -> None:
        self.closed = True


def test_buffer_returns_only_newest_frame_once():
    source = ClosedSource()
    buffer = LatestFrameBuffer(source)
    buffer.push(SimpleNamespace(id=1))
    buffer.push(SimpleNamespace(id=2))
    ok, frame = buffer.read()
    assert ok is True
    assert frame.id == 2
    assert buffer.read() == (False, None)
    buffer.close()
    assert source.closed is True


def test_buffer_clear_drops_frames_from_previous_camera():
    buffer = LatestFrameBuffer(ClosedSource())
    buffer.push(SimpleNamespace(id="old"))
    buffer.clear()
    assert buffer.read() == (False, None)
    buffer.close()


def test_buffer_rejects_stale_frames():
    buffer = LatestFrameBuffer(ClosedSource(), max_age_seconds=0.01)
    buffer.push(SimpleNamespace(id=1), captured_at=time.monotonic() - 1)
    assert buffer.read() == (False, None)
    buffer.close()
