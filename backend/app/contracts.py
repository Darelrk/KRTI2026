from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


LinkState = Literal["connected", "stale", "disconnected"]
FlightMode = Literal["MANUAL", "AUTO", "HOLD", "ELS"]
CameraId = Literal["front", "down", "night"]
VisionClass = Literal["person", "aruco", "gate", "drop_zone", "line", "landing_pad"]
PayloadState = Literal["secured", "armed", "released", "unknown"]
ElsState = Literal["standby", "countdown", "active"]
MissionStatus = Literal["ready", "active", "passed", "failed", "retry"]
RetryCheckpoint = Literal["START", "WP1", "WP2", "WP4"]
CommandType = Literal[
    "arm",
    "enable_autonomy",
    "pause_mission",
    "retry",
    "emergency_land",
]


class EventBase(StrictModel):
    seq: int = Field(ge=0)
    timestampMs: int = Field(ge=0)


class GeoPoint(StrictModel):
    latitude: float
    longitude: float


class NormalizedPoint(StrictModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class NormalizedBox(NormalizedPoint):
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class TelemetryEvent(EventBase):
    type: Literal["telemetry"] = "telemetry"
    armed: bool
    mode: FlightMode
    batteryPercent: float = Field(ge=0, le=100)
    voltage: float = Field(ge=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    gpsFix: int = Field(ge=0)
    gpsSatellites: int = Field(ge=0)
    hdop: float | None = Field(default=None, ge=0)
    localXM: float | None = None
    localYM: float | None = None
    altitudeM: float
    rangefinderM: float | None = Field(default=None, ge=0)
    groundSpeedMps: float = Field(ge=0)
    headingDeg: float = Field(ge=0, lt=360)
    rollDeg: float
    pitchDeg: float
    yawDeg: float
    collisionClearanceM: float | None = Field(default=None, ge=0)


class VisionEvent(EventBase):
    type: Literal["vision"] = "vision"
    id: str
    frameId: int = Field(ge=0)
    camera: CameraId
    className: VisionClass
    confidence: float = Field(ge=0, le=1)
    box: NormalizedBox | None = None
    path: list[NormalizedPoint] | None = None
    markerId: int | None = None

    @model_validator(mode="after")
    def requires_geometry(self) -> VisionEvent:
        if self.box is None and not self.path:
            raise ValueError("vision event requires box or path geometry")
        return self


class VisionTarget(StrictModel):
    timestampMs: int = Field(ge=0)
    id: str
    frameId: int = Field(ge=0)
    camera: CameraId
    className: VisionClass
    confidence: float = Field(ge=0, le=1)
    box: NormalizedBox | None = None
    path: list[NormalizedPoint] | None = None
    markerId: int | None = None


class MissionEvent(EventBase):
    type: Literal["mission"] = "mission"
    phase: Literal[1, 2, 3, 4, 5]
    phaseName: str
    waypointLabel: str
    status: MissionStatus
    elapsedSeconds: int = Field(ge=0)
    score: int = Field(ge=0)
    retryCheckpoint: RetryCheckpoint
    autonomyReady: bool


class PayloadEvent(EventBase):
    type: Literal["payload"] = "payload"
    state: PayloadState


class SafetyEvent(EventBase):
    type: Literal["safety"] = "safety"
    linkLostSeconds: int = Field(ge=0)
    elsState: ElsState
    personWarning: bool
    obstacleWarning: bool


class MapEvent(EventBase):
    type: Literal["map"] = "map"
    baseAvailable: bool


class CameraEvent(EventBase):
    type: Literal["camera"] = "camera"
    id: CameraId
    connected: bool
    latencyMs: int = Field(ge=0)
    fps: float = Field(ge=0)


class LinkEvent(EventBase):
    type: Literal["link"] = "link"
    state: LinkState


class TrimVisionEvent(EventBase):
    type: Literal["trim_vision"] = "trim_vision"


FlightEvent = Annotated[
    Union[
        TelemetryEvent,
        VisionEvent,
        MissionEvent,
        PayloadEvent,
        SafetyEvent,
        MapEvent,
        CameraEvent,
        LinkEvent,
        TrimVisionEvent,
    ],
    Field(discriminator="type"),
]


class CameraState(StrictModel):
    id: CameraId
    connected: bool
    latencyMs: int = Field(ge=0)
    fps: float = Field(ge=0)


class MissionState(StrictModel):
    phase: Literal[1, 2, 3, 4, 5]
    phaseName: str
    waypointLabel: str
    status: MissionStatus
    elapsedSeconds: int = Field(ge=0)
    score: int = Field(ge=0)
    retryCheckpoint: RetryCheckpoint
    autonomyReady: bool


class SafetyState(StrictModel):
    linkLostSeconds: int = Field(ge=0)
    elsState: ElsState
    personWarning: bool
    personAcknowledged: bool
    obstacleWarning: bool


class MapState(StrictModel):
    baseAvailable: bool


class FlightSnapshot(StrictModel):
    telemetry: TelemetryEvent | None
    track: list[GeoPoint]
    link: LinkState
    camera: CameraState
    map: MapState
    mission: MissionState
    payload: PayloadState
    safety: SafetyState
    visionTargets: list[VisionTarget]
    lastEventAt: int = Field(ge=0)


class CommandRequest(StrictModel):
    commandId: str = Field(min_length=1)
    type: CommandType


class CommandResult(StrictModel):
    commandId: str
    status: Literal["accepted", "rejected", "unknown"]
    reason: str | None = None


class ComponentHealth(StrictModel):
    state: Literal["disabled", "disconnected", "connecting", "ready", "stale", "degraded"]
    lastEventAt: int | None = None
    error: str | None = None


class HealthResponse(StrictModel):
    status: Literal["ready", "degraded", "disconnected"]
    serial: ComponentHealth
    video: ComponentHealth
    inference: ComponentHealth
