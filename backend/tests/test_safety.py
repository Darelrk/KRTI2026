from backend.app.contracts import CommandRequest
from backend.app.safety import SafetyGate
from backend.tests.test_mavlink_writer import snapshot


def test_rejects_commands_when_serial_is_not_ready():
    result = SafetyGate().evaluate(
        CommandRequest(commandId="a", type="arm"), snapshot(link="disconnected")
    )
    assert result.allowed is False
    assert result.reason == "Serial link is not ready"


def test_rejects_duplicate_command_id():
    gate = SafetyGate()
    request = CommandRequest(commandId="a", type="pause_mission")
    gate.remember("a")
    result = gate.evaluate(request, snapshot())
    assert result.allowed is False
    assert result.reason == "Duplicate commandId"


def test_autonomy_requires_backend_readiness():
    result = SafetyGate().evaluate(
        CommandRequest(commandId="a", type="enable_autonomy"), snapshot()
    )
    assert result.allowed is False
    assert result.reason == "Autonomy is not ready at the current checkpoint"
