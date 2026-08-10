from __future__ import annotations

import asyncio

from .contracts import (
    CameraEvent,
    CameraState,
    FlightEvent,
    FlightSnapshot,
    GeoPoint,
    LinkEvent,
    MapEvent,
    MapState,
    MissionEvent,
    MissionState,
    PayloadEvent,
    SafetyEvent,
    SafetyState,
    TelemetryEvent,
    VisionEvent,
    VisionTarget,
)


def empty_snapshot() -> FlightSnapshot:
    return FlightSnapshot(
        telemetry=None,
        track=[],
        link="disconnected",
        camera=CameraState(id="front", connected=False, latencyMs=0, fps=0),
        map=MapState(baseAvailable=True),
        mission=MissionState(
            phase=1,
            phaseName="Manual navigation and transition",
            waypointLabel="START",
            status="ready",
            elapsedSeconds=0,
            score=0,
            retryCheckpoint="START",
            autonomyReady=False,
        ),
        payload="unknown",
        safety=SafetyState(
            linkLostSeconds=0,
            elsState="standby",
            personWarning=False,
            personAcknowledged=False,
            obstacleWarning=False,
        ),
        visionTargets=[],
        lastEventAt=0,
    )


class StateStore:
    def __init__(self, initial_snapshot: FlightSnapshot | None = None) -> None:
        self._snapshot = initial_snapshot or empty_snapshot()
        self._sequence = 0
        self._lock = asyncio.Lock()

    async def publish(self, event: FlightEvent) -> FlightEvent:
        async with self._lock:
            self._sequence += 1
            normalized = event.model_copy(update={"seq": self._sequence})
            self._snapshot = self._apply(normalized)
            return normalized

    async def snapshot(self) -> FlightSnapshot:
        async with self._lock:
            return self._snapshot.model_copy(deep=True)

    async def initial_events(self) -> list[FlightEvent]:
        snapshot = await self.snapshot()
        events: list[FlightEvent] = []
        if snapshot.telemetry is not None:
            events.append(snapshot.telemetry)
        events.extend(
            [
                LinkEvent(seq=0, timestampMs=snapshot.lastEventAt, state=snapshot.link),
                CameraEvent(
                    seq=0,
                    timestampMs=snapshot.lastEventAt,
                    id=snapshot.camera.id,
                    connected=snapshot.camera.connected,
                    latencyMs=snapshot.camera.latencyMs,
                    fps=snapshot.camera.fps,
                ),
                MapEvent(
                    seq=0,
                    timestampMs=snapshot.lastEventAt,
                    baseAvailable=snapshot.map.baseAvailable,
                ),
                MissionEvent(
                    seq=0,
                    timestampMs=snapshot.lastEventAt,
                    **snapshot.mission.model_dump(),
                ),
                PayloadEvent(
                    seq=0,
                    timestampMs=snapshot.lastEventAt,
                    state=snapshot.payload,
                ),
                SafetyEvent(
                    seq=0,
                    timestampMs=snapshot.lastEventAt,
                    **snapshot.safety.model_dump(exclude={"personAcknowledged"}),
                ),
            ]
        )
        return events

    async def acknowledge_person_warning(self) -> None:
        async with self._lock:
            self._snapshot = self._snapshot.model_copy(
                update={
                    "safety": self._snapshot.safety.model_copy(
                        update={"personAcknowledged": True}
                    )
                }
            )

    def _apply(self, event: FlightEvent) -> FlightSnapshot:
        snapshot = self._snapshot
        update = {"lastEventAt": event.timestampMs}
        if isinstance(event, TelemetryEvent):
            track = list(snapshot.track)
            if event.latitude is not None and event.longitude is not None:
                track.append(
                    GeoPoint(latitude=event.latitude, longitude=event.longitude)
                )
                track = track[-121:]
            update.update(telemetry=event, track=track)
        elif isinstance(event, LinkEvent):
            update["link"] = event.state
        elif isinstance(event, CameraEvent):
            update["camera"] = CameraState(
                id=event.id,
                connected=event.connected,
                latencyMs=event.latencyMs,
                fps=event.fps,
            )
        elif isinstance(event, MapEvent):
            update["map"] = MapState(baseAvailable=event.baseAvailable)
        elif isinstance(event, MissionEvent):
            update["mission"] = MissionState(
                **event.model_dump(exclude={"type", "seq", "timestampMs"})
            )
        elif isinstance(event, PayloadEvent):
            update["payload"] = event.state
        elif isinstance(event, SafetyEvent):
            acknowledged = (
                snapshot.safety.personAcknowledged if event.personWarning else False
            )
            update["safety"] = SafetyState(
                **event.model_dump(exclude={"type", "seq", "timestampMs"}),
                personAcknowledged=acknowledged,
            )
        elif isinstance(event, VisionEvent):
            target = VisionTarget.model_validate(
                event.model_dump(exclude={"type", "seq"})
            )
            update["visionTargets"] = [target, *snapshot.visionTargets][:20]
        else:
            update["visionTargets"] = snapshot.visionTargets[:20]
        return snapshot.model_copy(update=update)
