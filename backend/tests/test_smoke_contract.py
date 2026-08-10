from fastapi.testclient import TestClient

from backend.app.event_bus import EventBus
from backend.app.runtime import Runtime, create_app
from backend.app.state_store import StateStore, empty_snapshot


def test_no_hardware_contract_is_dashboard_compatible():
    runtime = Runtime(
        store=StateStore(initial_snapshot=empty_snapshot()),
        event_bus=EventBus(),
    )
    with TestClient(create_app(runtime=runtime)) as client:
        health = client.get("/api/health")
        snapshot = client.get("/api/snapshot")
        with client.websocket_connect("/ws/flight") as websocket:
            event = websocket.receive_json()
    assert health.status_code == 200
    assert snapshot.status_code == 200
    assert event["type"] == "link"
    assert {"seq", "timestampMs", "state"} <= event.keys()
