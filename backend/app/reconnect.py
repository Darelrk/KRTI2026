from __future__ import annotations

from enum import StrEnum


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    STALE = "stale"


class ReconnectPolicy:
    def __init__(self, max_seconds: float = 30.0) -> None:
        if max_seconds <= 0:
            raise ValueError("max_seconds must be positive")
        self.max_seconds = max_seconds

    def delay_for(self, attempt: int) -> float:
        if attempt < 0:
            raise ValueError("attempt must not be negative")
        return min(2**attempt, self.max_seconds)
