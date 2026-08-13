import pytest
from pydantic import TypeAdapter, ValidationError
from backend.app.contracts import (
    CommandRequest,
    CommandResult,
    FlightEvent,
    TelemetryEvent,
    VisionEvent,
)


def telemetry_payload() -> dict:
    return {
        "type": "telemetry",
        "seq": 1,
        "timestampMs": 1_000,
        "armed": True,
        "mode": "AUTO",
        "batteryPercent": 72,
        "voltage": 15.9,
        "latitude": None,
        "longitude": None,
        "gpsFix": 0,
        "gpsSatellites": 0,
        "hdop": None,
        "localXM": 12.5,
        "localYM": 8.25,
        "altitudeM": 6.4,
        "rangefinderM": 5.9,
        "groundSpeedMps": 2.3,
        "headingDeg": 91,
        "rollDeg": 1.2,
        "pitchDeg": -0.7,
        "yawDeg": 91,
        "collisionClearanceM": None,
    }


def test_telemetry_preserves_unavailable_values_as_null():
    telemetry = TelemetryEvent.model_validate(telemetry_payload())
    assert telemetry.latitude is None
    assert telemetry.rangefinderM == 5.9


def test_flight_event_dispatches_to_typed_event():
    event = TypeAdapter(FlightEvent).validate_python(telemetry_payload())
    assert isinstance(event, TelemetryEvent)
    assert event.type == "telemetry"


def test_vision_requires_geometry():
    with pytest.raises(ValidationError):
        VisionEvent.model_validate(
            {
                "type": "vision",
                "seq": 1,
                "timestampMs": 1,
                "id": "target-1",
                "frameId": 1,
                "camera": "front",
                "className": "person",
                "confidence": 0.8,
            }
        )


def test_commands_reject_unknown_fields():
    with pytest.raises(ValidationError):
        CommandRequest.model_validate(
            {"commandId": "a", "type": "arm", "unexpected": True}
        )


def test_command_result_has_explicit_unknown_status():
    result = CommandResult(
        commandId="a", status="unknown", reason="No acknowledgment"
    )
    assert result.status == "unknown"


def test_vision_accepts_night_camera():
    event = VisionEvent.model_validate(
        {
            "type": "vision",
            "seq": 1,
            "timestampMs": 1,
            "id": "night-1",
            "frameId": 1,
            "camera": "night",
            "className": "person",
            "confidence": 0.8,
            "box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
        }
    )
    assert event.camera == "night"