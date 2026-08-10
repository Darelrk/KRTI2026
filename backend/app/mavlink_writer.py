from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from .contracts import CommandRequest, CommandResult, FlightSnapshot
from .safety import SafetyGate


@dataclass(frozen=True)
class OutboundCommand:
    command: str
    parameters: tuple[float, ...] = ()


class MavlinkWriterTransport(Protocol):
    def send(self, message: OutboundCommand) -> None: ...


class MavlinkWriter:
    """Single-owner, fail-closed command writer with no flight-command retries."""

    def __init__(
        self,
        transport: MavlinkWriterTransport,
        gate: SafetyGate | None = None,
        timeout_seconds: float = 2.0,
    ) -> None:
        self.transport = transport
        self.gate = gate or SafetyGate()
        self.timeout_seconds = timeout_seconds
        self._lock = asyncio.Lock()

    def send_command(
        self, request: CommandRequest, snapshot: FlightSnapshot
    ) -> CommandResult:
        decision = self.gate.evaluate(request, snapshot)
        if not decision.allowed:
            return self._rejected(request, decision.reason)
        self.gate.remember(request.commandId)
        try:
            self.transport.send(self._encode(request.type))
        except Exception:
            return self._result(request, "unknown", "transport error")
        return self._result(request, "accepted")

    async def execute(
        self, request: CommandRequest, snapshot: FlightSnapshot
    ) -> CommandResult:
        async with self._lock:
            decision = self.gate.evaluate(request, snapshot)
            if not decision.allowed:
                return self._rejected(request, decision.reason)
            self.gate.remember(request.commandId)
            try:
                await asyncio.to_thread(self.transport.send, self._encode(request.type))
            except Exception:
                return self._result(request, "unknown", "transport error")
            wait_ack = getattr(self.transport, "wait_ack", None)
            if not callable(wait_ack):
                return self._result(request, "accepted")
            try:
                acknowledged = await asyncio.wait_for(
                    asyncio.to_thread(wait_ack, request.type, self.timeout_seconds),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                return self._result(request, "unknown", "acknowledgment timeout")
            except Exception:
                return self._result(request, "unknown", "acknowledgment error")
            if not acknowledged:
                return self._result(request, "unknown", "acknowledgment timeout")
            return self._result(request, "accepted")

    @staticmethod
    def _rejected(request: CommandRequest, reason: str | None) -> CommandResult:
        return CommandResult(commandId=request.commandId, status="rejected", reason=reason)

    @staticmethod
    def _result(
        request: CommandRequest, status: str, reason: str | None = None
    ) -> CommandResult:
        return CommandResult(commandId=request.commandId, status=status, reason=reason)  # type: ignore[arg-type]

    @staticmethod
    def _encode(command: str) -> OutboundCommand:
        return OutboundCommand(
            command=command,
            parameters={
                "arm": (1.0,),
                "enable_autonomy": (1.0,),
                "pause_mission": (0.0,),
                "retry": (0.0,),
                "emergency_land": (0.0,),
            }[command],
        )
