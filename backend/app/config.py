from __future__ import annotations

import math

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .contracts import CameraId


class ConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CameraProfile:
    id: CameraId
    video_url: str | None
    model_path: Path


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    pixhawk_serial: str | None = None
    pixhawk_baud: int = 115200
    front_video_url: str | None = None
    down_video_url: str | None = None
    night_video_url: str | None = None
    regular_model_path: Path = Path("model/best.pt")
    night_model_path: Path = Path("model/yolo26xthermal.pt")
    active_camera: CameraId = "front"
    inference_conf: float = 0.25
    max_fps: float = 10.0
    serial_reconnect_max_seconds: float = 30.0
    command_timeout_seconds: float = 2.0
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:3000",)

    @property
    def serial_enabled(self) -> bool:
        return self.pixhawk_serial is not None

    @property
    def video_url(self) -> str | None:
        return self.front_video_url

    @property
    def model_path(self) -> Path:
        return self.regular_model_path

    @property
    def video_enabled(self) -> bool:
        return any(profile.video_url for profile in self.camera_profiles.values())

    @property
    def camera_profiles(self) -> dict[CameraId, CameraProfile]:
        return {
            "front": CameraProfile("front", self.front_video_url, self.regular_model_path),
            "down": CameraProfile("down", self.down_video_url, self.regular_model_path),
            "night": CameraProfile("night", self.night_video_url, self.night_model_path),
        }

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> Settings:
        defaults = cls()
        host = _text(environ, "HOST", defaults.host)
        if host == "0.0.0.0":
            raise ConfigError("HOST must not bind publicly by default")
        port = _positive_int(environ, "PORT", defaults.port)
        baud = _positive_int(environ, "PIXHAWK_BAUD", defaults.pixhawk_baud)
        inference_conf = _float(environ, "INFERENCE_CONF", defaults.inference_conf)
        if not 0 <= inference_conf <= 1:
            raise ConfigError("INFERENCE_CONF must be between 0 and 1")
        max_fps = _positive_float(environ, "MAX_FPS", defaults.max_fps)
        reconnect_max = _positive_float(
            environ, "SERIAL_RECONNECT_MAX_SECONDS", defaults.serial_reconnect_max_seconds
        )
        command_timeout = _positive_float(
            environ, "COMMAND_TIMEOUT_SECONDS", defaults.command_timeout_seconds
        )
        origins = _origins(environ.get("CORS_ORIGINS"), defaults.cors_origins)
        return cls(
            host=host,
            port=port,
            pixhawk_serial=_optional_text(environ.get("PIXHAWK_SERIAL")),
            pixhawk_baud=baud,
            front_video_url=_optional_text(environ.get("FRONT_VIDEO_URL"))
            or _optional_text(environ.get("VIDEO_URL")),
            down_video_url=_optional_text(environ.get("DOWN_VIDEO_URL")),
            night_video_url=_optional_text(environ.get("NIGHT_VIDEO_URL")),
            regular_model_path=Path(
                _text(
                    environ,
                    "REGULAR_MODEL_PATH",
                    _text(environ, "MODEL_PATH", str(defaults.regular_model_path)),
                )
            ),
            night_model_path=Path(
                _text(environ, "NIGHT_MODEL_PATH", str(defaults.night_model_path))
            ),
            active_camera=_camera_id(environ.get("ACTIVE_CAMERA"), defaults.active_camera),
            inference_conf=inference_conf,
            max_fps=max_fps,
            serial_reconnect_max_seconds=reconnect_max,
            command_timeout_seconds=command_timeout,
            cors_origins=origins,
        )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None

def _camera_id(value: str | None, default: CameraId) -> CameraId:
    camera = _optional_text(value) or default
    if camera not in {"front", "down", "night"}:
        raise ConfigError("ACTIVE_CAMERA must be front, down, or night")
    return camera  # type: ignore[return-value]


def _text(environ: Mapping[str, str], name: str, default: str) -> str:
    return _optional_text(environ.get(name)) or default


def _positive_int(environ: Mapping[str, str], name: str, default: int) -> int:
    raw = _text(environ, name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be positive")
    return value


def _float(environ: Mapping[str, str], name: str, default: float) -> float:
    raw = _text(environ, name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc
    if not math.isfinite(value):
        raise ConfigError(f"{name} must be finite")
    return value


def _positive_float(environ: Mapping[str, str], name: str, default: float) -> float:
    value = _float(environ, name, default)
    if value <= 0:
        raise ConfigError(f"{name} must be positive")
    return value


def _origins(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None or not value.strip():
        return default
    origins = tuple(item.strip() for item in value.split(",") if item.strip())
    if not origins or "*" in origins:
        raise ConfigError("CORS_ORIGINS must contain explicit origins")
    return origins
