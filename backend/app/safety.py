from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable

from .contracts import CommandRequest, FlightSnapshot


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str | None = None


class SafetyGate:
    ALLOWED_COMMANDS = {
        "arm",
        "enable_autonomy",
        "pause_mission",
        "retry",
        "emergency_land",
    }

    def __init__(
        self,
        clock: Callable[[], float] = monotonic,
        max_ids: int = 256,
        id_ttl_seconds: float = 300.0,
    ) -> None:
        self.clock = clock
        self.max_ids = max_ids
        self.id_ttl_seconds = id_ttl_seconds
        self._processed: dict[str, float] = {}

    def evaluate(self, request: CommandRequest, state: FlightSnapshot) -> GateDecision:
        self.clear_expired_ids()
        if request.type not in self.ALLOWED_COMMANDS:
            return GateDecision(False, "Command type is not allowed")
        if request.commandId in self._processed:
            return GateDecision(False, "Duplicate commandId")
        if state.link != "connected" or state.telemetry is None:
            return GateDecision(False, "Serial link is not ready")
        telemetry = state.telemetry
        if request.type == "arm":
            if telemetry.gpsFix < 3 or telemetry.gpsSatellites < 5:
                return GateDecision(False, "Pre-arm checks failed")
            if telemetry.batteryPercent < 20:
                return GateDecision(False, "Pre-arm checks failed")
        elif request.type == "enable_autonomy":
            if not state.mission.autonomyReady:
                return GateDecision(False, "Autonomy is not ready at the current checkpoint")
            if not telemetry.armed or telemetry.gpsFix < 3:
                return GateDecision(False, "Autonomy preconditions failed")
        elif request.type in {"pause_mission", "retry", "emergency_land"}:
            if not telemetry.armed:
                return GateDecision(False, "Vehicle is not armed")
        return GateDecision(True)

    def remember(self, command_id: str) -> None:
        self.clear_expired_ids()
        self._processed[command_id] = self.clock()
        if len(self._processed) > self.max_ids:
            oldest = min(self._processed, key=self._processed.__getitem__)
            del self._processed[oldest]

    def clear_expired_ids(self) -> None:
        cutoff = self.clock() - self.id_ttl_seconds
        for command_id, created_at in tuple(self._processed.items()):
            if created_at <= cutoff:
                del self._processed[command_id]
