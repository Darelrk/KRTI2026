from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .contracts import (
    CommandRequest,
    CommandResult,
    ComponentHealth,
    FlightEvent,
    HealthResponse,
    LinkEvent,
)
from .event_bus import EventBus
from .inference import OpenCVFrameSource, RTSPInference, UltralyticsPersonDetector
from .mavlink_reader import MavlinkReader
from .mavlink_writer import MavlinkWriter, OutboundCommand
from .reconnect import ReconnectPolicy
from .state_store import StateStore
from .video_ingest import LatestFrameBuffer


class Runtime:
    def __init__(
        self,
        store: StateStore,
        event_bus: EventBus,
        writer: MavlinkWriter | None = None,
        reader: MavlinkReader | None = None,
        inference: RTSPInference | None = None,
        serial_error: str | None = None,
        video_error: str | None = None,
        reconnect_policy: ReconnectPolicy | None = None,
    ) -> None:
        self.store = store
        self.event_bus = event_bus
        self.writer = writer
        self.reader = reader
        self.inference = inference
        self.serial_error = serial_error
        self.video_error = video_error
        self.reconnect_policy = reconnect_policy or ReconnectPolicy()
        self._stop = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        self._stop.clear()
        if self.inference is not None:
            start = getattr(self.inference.source, "start", None)
            if callable(start):
                start()
        if self.reader is not None:
            self._tasks.append(asyncio.create_task(self._serial_loop()))
        if self.inference is not None:
            self._tasks.append(asyncio.create_task(self._inference_loop()))


    async def stop(self) -> None:
        self._stop.set()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self.inference is not None:
            self.inference.close()
        if self.reader is not None:
            close = getattr(self.reader.transport, "close", None)
            if callable(close):
                close()

    async def snapshot(self) -> dict[str, Any]:
        return (await self.store.snapshot()).model_dump(mode="json")

    async def command(self, request: CommandRequest) -> CommandResult:
        if self.writer is None:
            return CommandResult(
                commandId=request.commandId,
                status="rejected",
                reason="serial is disabled",
            )
        return await self.writer.execute(request, await self.store.snapshot())

    async def health(self) -> HealthResponse:
        snapshot = await self.store.snapshot()
        serial_state = self._serial_state(snapshot.link)
        video_state = self._video_state()
        inference_state = self._inference_state()
        states = {serial_state, video_state, inference_state}
        if "degraded" in states:
            status = "degraded"
        elif "ready" in states:
            status = "ready"
        else:
            status = "disconnected"
        last_event = snapshot.lastEventAt or None
        return HealthResponse(
            status=status,
            serial=ComponentHealth(
                state=serial_state,
                lastEventAt=last_event,
                error=self.serial_error,
            ),
            video=ComponentHealth(
                state=video_state,
                lastEventAt=last_event,
                error=self.video_error,
            ),
            inference=ComponentHealth(
                state=inference_state,
                lastEventAt=last_event,
                error=self.inference.last_error if self.inference else None,
            ),
        )
    async def _serial_loop(self) -> None:
        assert self.reader is not None
        attempt = 0
        while not self._stop.is_set():
            try:
                events = await self.reader.poll_once()
                attempt = 0
                for event in events:
                    await self.event_bus.publish(event)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.serial_error = str(error)
                disconnected = LinkEvent(
                    seq=0,
                    timestampMs=int(asyncio.get_running_loop().time() * 1000),
                    state="disconnected",
                )
                published = await self.store.publish(disconnected)
                await self.event_bus.publish(published)
                reconnect = getattr(self.reader.transport, "reconnect", None)
                if callable(reconnect):
                    await asyncio.to_thread(reconnect)
                delay = self.reconnect_policy.delay_for(attempt)
                attempt += 1
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass

    async def _inference_loop(self) -> None:
        assert self.inference is not None
        while not self._stop.is_set():
            try:
                events = await self.inference.publish_once()
                for event in events:
                    await self.event_bus.publish(event)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.video_error = str(error)
                self.inference.health_state = "degraded"
                events = []
            if not events:
                await asyncio.sleep(0.05)

    def _serial_state(self, link: str) -> str:
        if self.reader is None:
            return "degraded" if self.serial_error else "disabled"
        return {"connected": "ready", "stale": "stale", "disconnected": "disconnected"}[link]

    def _video_state(self) -> str:
        if self.inference is None:
            return "degraded" if self.video_error else "disabled"
        return self.inference.health_state

    def _inference_state(self) -> str:
        if self.inference is None:
            return "disabled"
        return self.inference.health_state


@asynccontextmanager
async def _lifespan(app: FastAPI):
    runtime: Runtime = app.state.runtime
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()


def create_app(
    settings: Settings | None = None,
    runtime: Runtime | None = None,
) -> FastAPI:
    runtime = runtime or build_runtime(settings or Settings())
    app = FastAPI(title="KRTI VTOL Backend", lifespan=_lifespan)
    app.state.runtime = runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins if settings else ("http://127.0.0.1:3000",)),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return await runtime.health()

    @app.get("/api/snapshot")
    async def snapshot() -> dict[str, Any]:
        return await runtime.snapshot()

    @app.post("/api/commands", response_model=CommandResult)
    async def command(request: CommandRequest) -> CommandResult | JSONResponse:
        result = await runtime.command(request)
        if result.status == "accepted":
            return result
        if result.reason in {"serial is disabled", "Serial link is not ready"}:
            status_code = 503
        else:
            status_code = 409
        return JSONResponse(status_code=status_code, content=result.model_dump())

    @app.websocket("/ws/flight")
    async def events(websocket: WebSocket) -> None:
        await websocket.accept()
        subscription = runtime.event_bus.subscribe()
        try:
            for event in await runtime.store.initial_events():
                await websocket.send_json(event.model_dump(mode="json"))
            async for event in subscription:
                await websocket.send_json(event.model_dump(mode="json"))
        except WebSocketDisconnect:
            pass
        finally:
            await subscription.close()

    return app


def build_runtime(settings: Settings) -> Runtime:
    store = StateStore()
    event_bus = EventBus()
    serial_error: str | None = None
    video_error: str | None = None
    reader: MavlinkReader | None = None
    writer: MavlinkWriter | None = None
    inference: RTSPInference | None = None

    if settings.pixhawk_serial:
        try:
            from pymavlink import mavutil

            transport = _PymavlinkTransport(
                mavutil.mavlink_connection(
                    settings.pixhawk_serial, baud=settings.pixhawk_baud
                ),
                settings.pixhawk_serial,
                settings.pixhawk_baud,
            )
            reader = MavlinkReader(transport=transport, store=store)
            writer = MavlinkWriter(
                transport=transport,
                timeout_seconds=settings.command_timeout_seconds,
            )
        except Exception as error:
            serial_error = str(error)

    if settings.video_url:
        try:
            model_path = Path(settings.model_path)
            if not model_path.exists():
                raise FileNotFoundError(f"model not found: {model_path}")
            source = LatestFrameBuffer(OpenCVFrameSource(settings.video_url))
            inference = RTSPInference(
                source=source,
                detector=UltralyticsPersonDetector(str(model_path)),
                store=store,
                confidence=settings.inference_conf,
            )
        except Exception as error:
            video_error = str(error)

    return Runtime(
        store=store,
        event_bus=event_bus,
        writer=writer,
        reader=reader,
        inference=inference,
        serial_error=serial_error,
        video_error=video_error,
        reconnect_policy=ReconnectPolicy(settings.serial_reconnect_max_seconds),
    )


class _PymavlinkTransport:
    def __init__(self, connection: Any, device: str, baud: int) -> None:
        self.connection = connection
        self.device = device
        self.baud = baud
    def recv_match(self, *, blocking: bool, timeout: float) -> object | None:
        return self.connection.recv_match(blocking=blocking, timeout=timeout)
    def reconnect(self) -> None:
        from pymavlink import mavutil

        self.close()
        self.connection = mavutil.mavlink_connection(self.device, baud=self.baud)

    def send(self, message: OutboundCommand) -> None:
        command_ids = {
            "arm": 400,
            "enable_autonomy": 176,
            "pause_mission": 176,
            "retry": 300,
            "emergency_land": 21,
        }
        parameters = list(message.parameters) + [0.0] * 6
        encoded = self.connection.mav.command_long_encode(
            self.connection.target_system,
            self.connection.target_component,
            command_ids[message.command],
            0,
            *parameters[:7],
        )
        self.connection.mav.send(encoded)

    def close(self) -> None:
        close = getattr(self.connection, "close", None)
        if callable(close):
            close()


app = create_app(Settings.from_env(os.environ))
