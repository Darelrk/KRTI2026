from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.app.camera_switcher import CameraSwitcher, CameraSwitchError
from backend.app.config import CameraProfile
from backend.app.event_bus import EventBus
from backend.app.state_store import StateStore


class FakeSource:
    def __init__(self, url: str) -> None:
        self.url = url
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def read(self) -> tuple[bool, object | None]:
        return False, None

    def close(self) -> None:
        self.closed = True


class FakeDetector:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path

    def detect(self, frame: object, confidence: float) -> list[object]:
        return []


class FakeHardwareSwitcher:
    def __init__(self) -> None:
        self.selected: list[str] = []

    async def select(self, camera: str) -> None:
        self.selected.append(camera)


def make_switcher(
    tmp_path: Path, night_model: Path | None = None
) -> tuple[CameraSwitcher, list[FakeSource]]:
    regular_model = tmp_path / "regular.pt"
    regular_model.touch()
    if night_model is None:
        night_model = tmp_path / "night.pt"
        night_model.touch()
    sources: list[FakeSource] = []

    def source_factory(url: str) -> FakeSource:
        source = FakeSource(url)
        sources.append(source)
        return source

    def detector_factory(path: str) -> FakeDetector:
        return FakeDetector(path)

    switcher = CameraSwitcher(
        profiles={
            "front": CameraProfile("front", "front", regular_model),
            "down": CameraProfile("down", "down", regular_model),
            "night": CameraProfile("night", "night", night_model),
        },
        store=StateStore(),
        event_bus=EventBus(),
        source_factory=source_factory,
        detector_factory=detector_factory,
    )
    return switcher, sources


@pytest.mark.asyncio
async def test_switch_closes_old_source_and_uses_matching_model(tmp_path: Path):
    switcher, sources = make_switcher(tmp_path)
    await switcher.start("front")
    old = switcher.active_source

    result = await switcher.switch("night")

    assert result["camera"] == "night"
    assert old.closed is True
    assert switcher.active_model_path == tmp_path / "night.pt"
    assert switcher.active_source is not old
    assert switcher.active_source.started is True
    assert len(sources) == 2


@pytest.mark.asyncio
async def test_missing_model_is_rejected_before_closing_active_source(tmp_path: Path):
    missing = tmp_path / "missing.pt"
    switcher, _ = make_switcher(tmp_path, night_model=missing)
    await switcher.start("front")
    old = switcher.active_source

    with pytest.raises(CameraSwitchError, match="model"):
        await switcher.switch("night")

    assert old.closed is False
    assert switcher.active_camera == "front"


@pytest.mark.asyncio
async def test_concurrent_switches_are_serialized(tmp_path: Path):
    switcher, sources = make_switcher(tmp_path)
    await switcher.start("front")

    await asyncio.gather(switcher.switch("down"), switcher.switch("night"))

    assert switcher.active_camera in {"down", "night"}
    assert sum(not source.closed for source in sources) == 1



@pytest.mark.asyncio
async def test_shared_receiver_calls_hardware_adapter_and_keeps_one_source(tmp_path: Path):
    regular_model = tmp_path / "regular.pt"
    night_model = tmp_path / "night.pt"
    regular_model.touch()
    night_model.touch()
    selector = FakeHardwareSwitcher()
    sources: list[FakeSource] = []

    switcher = CameraSwitcher(
        profiles={
            "front": CameraProfile("front", "receiver", regular_model),
            "down": CameraProfile("down", "receiver", regular_model),
            "night": CameraProfile("night", "receiver", night_model),
        },
        store=StateStore(),
        event_bus=EventBus(),
        source_factory=lambda url: sources.append(FakeSource(url)) or sources[-1],
        detector_factory=FakeDetector,
        hardware_switcher=selector,
    )
    await switcher.start("front")
    source = switcher.active_source

    result = await switcher.switch("night")

    assert result["camera"] == "night"
    assert selector.selected == ["night"]
    assert switcher.active_source is source
    assert source.closed is False
    assert len(sources) == 1


@pytest.mark.asyncio
async def test_shared_receiver_without_adapter_fails_closed(tmp_path: Path):
    regular_model = tmp_path / "regular.pt"
    regular_model.touch()
    switcher = CameraSwitcher(
        profiles={
            "front": CameraProfile("front", "receiver", regular_model),
            "down": CameraProfile("down", "receiver", regular_model),
            "night": CameraProfile("night", None, regular_model),
        },
        store=StateStore(),
        event_bus=EventBus(),
        source_factory=lambda url: FakeSource(url),
        detector_factory=FakeDetector,
    )
    await switcher.start("front")
    source = switcher.active_source

    with pytest.raises(CameraSwitchError, match="HardwareSwitcher"):
        await switcher.switch("down")

    assert switcher.active_camera == "front"
    assert source.closed is False
