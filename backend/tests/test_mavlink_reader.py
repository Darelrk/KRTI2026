from types import SimpleNamespace

from backend.app.contracts import LinkEvent, TelemetryEvent
from backend.app.mavlink_reader import MavlinkReader
from backend.app.state_store import StateStore, empty_snapshot


class FakeTransport:
    def recv_match(self, *, blocking: bool, timeout: float):
        return None

    def send(self, message: object) -> None:
        pass

    def close(self) -> None:
        pass


def message(name: str, **fields: object) -> SimpleNamespace:
    item = SimpleNamespace(**fields)
    item.get_type = lambda: name
    return item


def reader() -> MavlinkReader:
    return MavlinkReader(
        transport=FakeTransport(),
        store=StateStore(initial_snapshot=empty_snapshot()),
        clock=lambda: 100.0,
    )


def latest_telemetry(events: list[object]) -> TelemetryEvent:
    return next(event for event in events if isinstance(event, TelemetryEvent))


def test_heartbeat_maps_mode_armed_and_connected_link():
    current = reader()
    events = current.consume_message(
        message("HEARTBEAT", base_mode=128, custom_mode=4, mode="AUTO")
    )
    telemetry = latest_telemetry(events)
    assert telemetry.armed is True
    assert telemetry.mode == "AUTO"
    assert next(event for event in events if isinstance(event, LinkEvent)).state == "connected"


def test_position_and_gps_messages_map_valid_values():
    current = reader()
    current.consume_message(
        message(
            "GLOBAL_POSITION_INT",
            lat=-77706000,
            lon=1103776000,
            relative_alt=6400,
        )
    )
    events = current.consume_message(
        message("GPS_RAW_INT", fix_type=3, satellites_visible=12, eph=80)
    )
    telemetry = latest_telemetry(events)
    assert telemetry.latitude == -7.7706
    assert telemetry.longitude == 110.3776
    assert telemetry.altitudeM == 6.4
    assert telemetry.gpsFix == 3
    assert telemetry.gpsSatellites == 12
    assert telemetry.hdop == 0.8


def test_attitude_distance_and_speed_are_converted():
    current = reader()
    current.consume_message(message("ATTITUDE", roll=0.1, pitch=-0.2, yaw=1.0))
    current.consume_message(message("DISTANCE_SENSOR", current_distance=590))
    events = current.consume_message(
        message("VFR_HUD", groundspeed=2.3, heading=91)
    )
    telemetry = latest_telemetry(events)
    assert telemetry.rollDeg > 5
    assert telemetry.pitchDeg < -10
    assert telemetry.rangefinderM == 5.9
    assert telemetry.groundSpeedMps == 2.3
    assert telemetry.headingDeg == 91


def test_invalid_position_remains_unavailable():
    current = reader()
    events = current.consume_message(
        message("GLOBAL_POSITION_INT", lat=0, lon=0, relative_alt=0)
    )
    telemetry = latest_telemetry(events)
    assert telemetry.latitude is None
    assert telemetry.longitude is None


def test_heartbeat_freshness_transitions_to_stale_and_disconnected():
    now = [100.0]
    current = MavlinkReader(
        transport=FakeTransport(),
        store=StateStore(initial_snapshot=empty_snapshot()),
        clock=lambda: now[0],
    )
    current.consume_message(message("HEARTBEAT", base_mode=0, custom_mode=0, mode="MANUAL"))
    now[0] = 102.1
    assert current.freshness_state() == "stale"
    now[0] = 105.1
    assert current.freshness_state() == "disconnected"
