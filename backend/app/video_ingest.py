from __future__ import annotations

import threading
import time
from typing import Any


class LatestFrameBuffer:
    """Keep one newest frame and never let a slow detector block capture."""

    def __init__(self, source: Any, max_age_seconds: float = 1.0) -> None:
        self.source = source
        self.max_age_seconds = max_age_seconds
        self._condition = threading.Condition()
        self._latest: object | None = None
        self._latest_at = 0.0
        self._sequence = 0
        self._read_sequence = 0
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stopped.clear()
        self._thread = threading.Thread(target=self._capture, name="rtsp-capture", daemon=True)
        self._thread.start()

    def push(self, frame: object, captured_at: float | None = None) -> None:
        with self._condition:
            self._latest = frame
            self._latest_at = captured_at if captured_at is not None else time.monotonic()
            self._sequence += 1
            self._condition.notify_all()

    def read(self) -> tuple[bool, object | None]:
        with self._condition:
            if self._latest is None or self._sequence == self._read_sequence:
                return False, None
            if time.monotonic() - self._latest_at > self.max_age_seconds:
                return False, None
            self._read_sequence = self._sequence
            return True, self._latest

    def clear(self) -> None:
        """Drop frames captured before a physical camera switch."""
        with self._condition:
            self._latest = None
            self._read_sequence = self._sequence

    def close(self) -> None:
        self._stopped.set()
        close = getattr(self.source, "close", None)
        if callable(close):
            close()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
        self._thread = None

    def _capture(self) -> None:
        while not self._stopped.is_set():
            try:
                ok, frame = self.source.read()
            except Exception as error:
                self.last_error = str(error)
                return
            if ok and frame is not None:
                self.push(frame)
            elif self._stopped.wait(0.05):
                return
