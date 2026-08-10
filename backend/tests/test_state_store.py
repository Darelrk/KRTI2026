import pytest

from backend.app.contracts import (
    LinkEvent,
    SafetyEvent,
    TelemetryEvent,
    VisionEvent,
)
from backend.app.event_bus import EventBus, EventOverflow
from backend.app.state_store import StateStore, empty_snapshot


def telemetry(seq: int = 0, latitude: float | None = -7.7) -> TelemetryEvent:
    return TelemetryEvent(
        seq=seq,
        timestampMs=1_000,
        armed=True,
        mode="AUTO",
        batteryPercent=70,
        voltage=15.9,
        latitude=latitude,
        longitude=110.3 if latitude is not None else None,
        gpsFix=3 if latitude is not None else 0,
        gpsSatellites=12 if latitude is not None else 0,
        hdop=0.8 if latitude is not None else None,
        localXM=None,
        localYM=None,
        altitudeM=5,
        rangefinderM=4,
        groundSpeedMps=1,
        headingDeg=90,
        rollDeg=0,
        pitchDeg=0,
        yawDeg=90,
        collisionClearanceM=None,
    )


@pytest.mark.asyncio
async def test_store_increments_sequence_and_returns_latest_snapshot():
    store = StateStore(initial_snapshot=empty_snapshot())
    event = await store.publish(LinkEvent(seq=0, timestampMs=1, state="connected"))
    snapshot = await store.snapshot()
    assert event.seq == 1
    assert snapshot.link == "connected"


@pytest.mark.asyncio
async def test_store_caps_track_and_does_not_add_no_fix_positions():
    store = StateStore(initial_snapshot=empty_snapshot())
    for index in range(130):
        await store.publish(telemetry(seq=index, latitude=-7.7 + index * 0.0001))
    await store.publish(telemetry(seq=131, latitude=None))
    snapshot = await store.snapshot()
    assert len(snapshot.track) == 121
    assert snapshot.track[0].latitude == pytest.approx(-7.6991)
    assert snapshot.telemetry.latitude is None


@pytest.mark.asyncio
async def test_safety_acknowledgment_is_preserved_until_warning_clears():
    store = StateStore(initial_snapshot=empty_snapshot())
    await store.publish(
        SafetyEvent(
            seq=1,
            timestampMs=1,
            linkLostSeconds=0,
            elsState="standby",
            personWarning=True,
            obstacleWarning=False,
        )
    )
    await store.acknowledge_person_warning()
    acknowledged = await store.snapshot()
    assert acknowledged.safety.personAcknowledged is True
    await store.publish(
        SafetyEvent(
            seq=2,
            timestampMs=2,
            linkLostSeconds=0,
            elsState="standby",
            personWarning=False,
            obstacleWarning=False,
        )
    )
    assert (await store.snapshot()).safety.personAcknowledged is False


@pytest.mark.asyncio
async def test_event_bus_preserves_order_for_subscriber():
    bus = EventBus(max_queue_size=2)
    subscription = bus.subscribe()
    await bus.publish(LinkEvent(seq=1, timestampMs=1, state="connected"))
    await bus.publish(LinkEvent(seq=2, timestampMs=2, state="stale"))
    assert (await subscription.get()).seq == 1
    assert (await subscription.get()).seq == 2
    await subscription.close()


@pytest.mark.asyncio
async def test_event_bus_reports_overflow_when_only_critical_events_remain():
    bus = EventBus(max_queue_size=1)
    subscription = bus.subscribe()
    await bus.publish(LinkEvent(seq=1, timestampMs=1, state="connected"))
    with pytest.raises(EventOverflow):
        await bus.publish(LinkEvent(seq=2, timestampMs=2, state="stale"))
    await subscription.close()
