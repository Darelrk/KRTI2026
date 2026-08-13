from fastapi.testclient import TestClient

from backend.app.event_bus import EventBus
from backend.app.mavlink_writer import MavlinkWriter
from backend.app.runtime import Runtime, create_app
from backend.app.state_store import StateStore, empty_snapshot


class FakeTransport:
    def send(self, message: object) -> None:
        pass


def app_client() -> TestClient:
    runtime = Runtime(
        store=StateStore(initial_snapshot=empty_snapshot()),
        event_bus=EventBus(),
        writer=MavlinkWriter(FakeTransport()),
    )
    return TestClient(create_app(runtime=runtime))


def test_health_and_snapshot_endpoints_are_available():
    with app_client() as client:
        health = client.get("/api/health")
        snapshot = client.get("/api/snapshot")
    assert health.status_code == 200
    assert health.json()["status"] == "disconnected"
    assert snapshot.status_code == 200
    assert snapshot.json()["telemetry"] is None


def test_camera_switch_endpoint_reports_disabled_selector():
    with app_client() as client:
        status = client.get("/api/cameras")
        response = client.post("/api/cameras/switch", json={"camera": "front"})

    assert status.status_code == 200
    assert status.json()["hardwareSwitcherConfigured"] is False
    assert response.status_code == 409
    assert "disabled" in response.json()["error"]


def test_command_endpoint_returns_fail_closed_result():
    with app_client() as client:
        response = client.post(
            "/api/commands",
            json={"commandId": "arm-1", "type": "arm"},
        )
    assert response.status_code == 503
    assert response.json() == {
        "commandId": "arm-1",
        "status": "rejected",
        "reason": "Serial link is not ready",
    }


def test_websocket_sends_initial_frontend_event_contract():
    with app_client() as client:
        with client.websocket_connect("/ws/flight") as websocket:
            event = websocket.receive_json()
    assert event["type"] == "link"
    assert event["seq"] == 0
    assert "timestampMs" in event
