import pytest

from backend.app.contracts import CommandRequest, FlightSnapshot, TelemetryEvent
from backend.app.mavlink_writer import MavlinkWriter
from backend.app.state_store import empty_snapshot


class FakeTransport:
    def __init__(self) -> None:
        self.messages: list[object] = []
        self.error: Exception | None = None
        self.ack: bool | None = None

    def send(self, message: object) -> None:
        if self.error:
            raise self.error
        self.messages.append(message)

    def wait_ack(self, command: str, timeout: float) -> bool | None:
        return self.ack


def telemetry(*, armed: bool = True, gps_fix: int = 3) -> TelemetryEvent:
    return TelemetryEvent(
        seq=1,
        timestampMs=1_000,
        armed=armed,
        mode="MANUAL",
        batteryPercent=80,
        voltage=15.9,
        latitude=-7.7,
        longitude=110.3,
        gpsFix=gps_fix,
        gpsSatellites=12,
        hdop=0.8,
        localXM=None,
        localYM=None,
        altitudeM=5,
        rangefinderM=4,
        groundSpeedMps=0,
        headingDeg=90,
        rollDeg=0,
        pitchDeg=0,
        yawDeg=90,
    )


def snapshot(*, link: str = "connected", armed: bool = True, gps_fix: int = 3) -> FlightSnapshot:
    result = empty_snapshot().model_copy(deep=True)
    result.link = link  # type: ignore[misc]
    result.telemetry = telemetry(armed=armed, gps_fix=gps_fix)  # type: ignore[misc]
    return result


def test_command_is_rejected_before_transport_when_link_is_unhealthy():
    transport = FakeTransport()
    writer = MavlinkWriter(transport=transport)
    result = writer.send_command(
        CommandRequest(commandId="arm-1", type="arm"),
        snapshot(link="stale"),
    )
    assert result.status == "rejected"
    assert result.reason == "Serial link is not ready"
    assert transport.messages == []


def test_arm_is_rejected_when_gps_prearm_gate_fails():
    transport = FakeTransport()
    writer = MavlinkWriter(transport=transport)
    result = writer.send_command(
        CommandRequest(commandId="arm-1", type="arm"),
        snapshot(armed=False, gps_fix=1),
    )
    assert result.status == "rejected"
    assert result.reason == "Pre-arm checks failed"
    assert transport.messages == []


def test_valid_emergency_land_is_sent_once_without_retry():
    transport = FakeTransport()
    writer = MavlinkWriter(transport=transport)
    result = writer.send_command(
        CommandRequest(commandId="land-1", type="emergency_land"),
        snapshot(),
    )
    assert result.status == "accepted"
    assert len(transport.messages) == 1
    assert transport.messages[0].command == "emergency_land"


def test_duplicate_command_id_is_rejected():
    transport = FakeTransport()
    writer = MavlinkWriter(transport=transport)
    request = CommandRequest(commandId="arm-1", type="arm")
    assert writer.send_command(request, snapshot()).status == "accepted"
    result = writer.send_command(request, snapshot())
    assert result.status == "rejected"
    assert result.reason == "Duplicate commandId"
    assert len(transport.messages) == 1


def test_transport_error_is_unknown_and_not_retried():
    transport = FakeTransport()
    transport.error = RuntimeError("serial down")
    writer = MavlinkWriter(transport=transport)
    result = writer.send_command(
        CommandRequest(commandId="land-1", type="emergency_land"),
        snapshot(),
    )
    assert result.status == "unknown"
    assert result.reason == "transport error"
    assert len(transport.messages) == 0


@pytest.mark.asyncio
async def test_missing_ack_returns_unknown_without_retry():
    transport = FakeTransport()
    transport.ack = False
    writer = MavlinkWriter(transport=transport, timeout_seconds=0.1)
    result = await writer.execute(
        CommandRequest(commandId="land-1", type="emergency_land"),
        snapshot(),
    )
    assert result.status == "unknown"
    assert result.reason == "acknowledgment timeout"
    assert len(transport.messages) == 1
