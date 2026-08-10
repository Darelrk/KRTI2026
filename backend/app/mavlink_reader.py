from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable, Protocol

from .contracts import LinkEvent, TelemetryEvent
from .state_store import StateStore


class MavlinkTransport(Protocol):
    def recv_match(self, *, blocking: bool, timeout: float) -> object | None: ...

    def send(self, message: object) -> None: ...

    def close(self) -> None: ...


Clock = Callable[[], float]


@dataclass
class _Telemetry:
    armed: bool = False
    mode: str = "MANUAL"
    battery_percent: float = 0.0
    voltage: float = 0.0
    latitude: float | None = None
    longitude: float | None = None
    gps_fix: int = 0
    gps_satellites: int = 0
    hdop: float | None = None
    local_x: float | None = None
    local_y: float | None = None
    altitude_m: float = 0.0
    rangefinder_m: float | None = None
    ground_speed_mps: float = 0.0
    heading_deg: float = 0.0
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0


class MavlinkReader:
    """Convert common ArduPilot MAVLink messages into normalized backend events."""

    STALE_AFTER_SECONDS = 2.0
    DISCONNECTED_AFTER_SECONDS = 5.0
    ARMED_FLAG = 128

    def __init__(
        self,
        transport: MavlinkTransport,
        store: StateStore,
        clock: Clock = monotonic,
    ) -> None:
        self.transport = transport
        self.store = store
        self.clock = clock
        self._telemetry = _Telemetry()
        self._seq = 0
        self._last_heartbeat: float | None = None
        self._last_link_state = "disconnected"

    def consume_message(self, message: object) -> list[LinkEvent | TelemetryEvent]:
        message_type = self._message_type(message)
        if message_type == "HEARTBEAT":
            self._heartbeat(message)
        elif message_type == "SYS_STATUS":
            self._sys_status(message)
        elif message_type == "GLOBAL_POSITION_INT":
            self._global_position(message)
        elif message_type == "GPS_RAW_INT":
            self._gps_raw(message)
        elif message_type == "LOCAL_POSITION_NED":
            self._local_position(message)
        elif message_type == "ATTITUDE":
            self._attitude(message)
        elif message_type == "DISTANCE_SENSOR":
            self._distance_sensor(message)
        elif message_type == "VFR_HUD":
            self._vfr_hud(message)
        else:
            return []

        events: list[LinkEvent | TelemetryEvent] = []
        if message_type == "HEARTBEAT":
            events.append(self._link_event(self._last_link_state))
        events.append(self._telemetry_event())
        return events

    async def poll_once(self, timeout: float = 0.5) -> list[LinkEvent | TelemetryEvent]:
        message = await asyncio.to_thread(
            self.transport.recv_match, blocking=True, timeout=timeout
        )
        events = self.consume_message(message) if message is not None else []
        if message is None:
            state = self.freshness_state()
            if state != self._last_link_state:
                self._last_link_state = state
                events = [self._link_event(state), self._telemetry_event()]
        published: list[LinkEvent | TelemetryEvent] = []
        for event in events:
            published.append(await self.store.publish(event))  # type: ignore[arg-type]
        return published

    def freshness_state(self) -> str:
        if self._last_heartbeat is None:
            return "disconnected"
        age = self.clock() - self._last_heartbeat
        if age > self.DISCONNECTED_AFTER_SECONDS:
            return "disconnected"
        if age > self.STALE_AFTER_SECONDS:
            return "stale"
        return "connected"

    @property
    def telemetry(self) -> TelemetryEvent:
        return self._telemetry_event()

    def _heartbeat(self, message: object) -> None:
        self._last_heartbeat = self.clock()
        self._last_link_state = "connected"
        base_mode = int(self._field(message, "base_mode", default=0) or 0)
        self._telemetry.armed = bool(base_mode & self.ARMED_FLAG)
        mode = self._field(message, "flightmode", "mode", default=None)
        if isinstance(mode, str):
            self._telemetry.mode = self._normalize_mode(mode)

    def _sys_status(self, message: object) -> None:
        voltage = self._field(message, "voltage_battery", default=None)
        if voltage is not None and float(voltage) >= 0:
            self._telemetry.voltage = float(voltage) / 1000.0
        battery = self._field(message, "battery_remaining", default=None)
        if battery is not None and int(battery) >= 0:
            self._telemetry.battery_percent = min(100.0, max(0.0, float(battery)))

    def _global_position(self, message: object) -> None:
        lat = self._scaled_coordinate(self._field(message, "lat", default=None), 1e-7)
        lon = self._scaled_coordinate(self._field(message, "lon", default=None), 1e-7)
        if lat is None or lon is None or (lat == 0 and lon == 0):
            self._telemetry.latitude = None
            self._telemetry.longitude = None
        else:
            self._telemetry.latitude = lat
            self._telemetry.longitude = lon
        relative_alt = self._field(message, "relative_alt", "alt", default=None)
        if relative_alt is not None:
            self._telemetry.altitude_m = float(relative_alt) / 1000.0

    def _gps_raw(self, message: object) -> None:
        fix = int(self._field(message, "fix_type", default=0) or 0)
        self._telemetry.gps_fix = max(0, fix)
        satellites = self._field(message, "satellites_visible", default=None)
        if satellites is not None:
            self._telemetry.gps_satellites = max(0, int(satellites))
        eph = self._field(message, "eph", default=None)
        if eph is not None and int(eph) < 65535:
            self._telemetry.hdop = max(0.0, float(eph) / 100.0)
        lat = self._scaled_coordinate(self._field(message, "lat", default=None), 1e-7)
        lon = self._scaled_coordinate(self._field(message, "lon", default=None), 1e-7)
        if fix >= 2 and lat is not None and lon is not None and not (lat == 0 and lon == 0):
            self._telemetry.latitude = lat
            self._telemetry.longitude = lon

    def _local_position(self, message: object) -> None:
        x = self._field(message, "x", default=None)
        y = self._field(message, "y", default=None)
        if x is not None:
            self._telemetry.local_x = float(x)
        if y is not None:
            self._telemetry.local_y = float(y)
        z = self._field(message, "z", default=None)
        if z is not None:
            self._telemetry.altitude_m = max(0.0, -float(z))

    def _attitude(self, message: object) -> None:
        self._telemetry.roll_deg = math.degrees(float(self._field(message, "roll", default=0.0)))
        self._telemetry.pitch_deg = math.degrees(float(self._field(message, "pitch", default=0.0)))
        yaw = math.degrees(float(self._field(message, "yaw", default=0.0)))
        self._telemetry.yaw_deg = yaw
        self._telemetry.heading_deg = self._heading(yaw)

    def _distance_sensor(self, message: object) -> None:
        distance_cm = self._field(message, "current_distance", default=None)
        if distance_cm is not None and float(distance_cm) >= 0:
            self._telemetry.rangefinder_m = float(distance_cm) / 100.0

    def _vfr_hud(self, message: object) -> None:
        speed = self._field(message, "groundspeed", default=None)
        if speed is not None:
            self._telemetry.ground_speed_mps = max(0.0, float(speed))
        heading = self._field(message, "heading", default=None)
        if heading is not None:
            self._telemetry.heading_deg = self._heading(float(heading))

    def _telemetry_event(self) -> TelemetryEvent:
        return TelemetryEvent(
            seq=self._next_seq(),
            timestampMs=self._timestamp_ms(),
            armed=self._telemetry.armed,
            mode=self._telemetry.mode,  # type: ignore[arg-type]
            batteryPercent=self._telemetry.battery_percent,
            voltage=self._telemetry.voltage,
            latitude=self._telemetry.latitude,
            longitude=self._telemetry.longitude,
            gpsFix=self._telemetry.gps_fix,
            gpsSatellites=self._telemetry.gps_satellites,
            hdop=self._telemetry.hdop,
            localXM=self._telemetry.local_x,
            localYM=self._telemetry.local_y,
            altitudeM=self._telemetry.altitude_m,
            rangefinderM=self._telemetry.rangefinder_m,
            groundSpeedMps=self._telemetry.ground_speed_mps,
            headingDeg=self._telemetry.heading_deg,
            rollDeg=self._telemetry.roll_deg,
            pitchDeg=self._telemetry.pitch_deg,
            yawDeg=self._telemetry.yaw_deg,
        )

    def _link_event(self, state: str) -> LinkEvent:
        return LinkEvent(seq=self._next_seq(), timestampMs=self._timestamp_ms(), state=state)  # type: ignore[arg-type]

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _timestamp_ms(self) -> int:
        return max(0, int(self.clock() * 1000))

    @staticmethod
    def _message_type(message: object) -> str:
        get_type = getattr(message, "get_type", None)
        if callable(get_type):
            return str(get_type()).upper()
        return str(getattr(message, "type", "")).upper()

    @staticmethod
    def _field(message: object, *names: str, default: Any) -> Any:
        for name in names:
            if isinstance(message, dict) and name in message:
                return message[name]
            value = getattr(message, name, None)
            if value is not None:
                return value
        return default

    @staticmethod
    def _scaled_coordinate(value: Any, scale: float) -> float | None:
        if value is None:
            return None
        result = float(value)
        if abs(result) > 180:
            result *= scale
        return result

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        normalized = mode.upper().strip().replace(" ", "_")
        aliases = {"STABILIZE": "MANUAL", "GUIDED": "AUTO", "LOITER": "HOLD"}
        normalized = aliases.get(normalized, normalized)
        return normalized if normalized in {"MANUAL", "AUTO", "HOLD", "ELS"} else "MANUAL"

    @staticmethod
    def _heading(value: float) -> float:
        return min(359.999, max(0.0, value % 360.0))
