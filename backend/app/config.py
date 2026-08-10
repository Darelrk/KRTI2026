from __future__ import annotations

import math

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    pixhawk_serial: str | None = None
    pixhawk_baud: int = 115200
    video_url: str | None = None
    model_path: Path = Path("model/best.pt")
    inference_conf: float = 0.25
    max_fps: float = 10.0
    serial_reconnect_max_seconds: float = 30.0
    command_timeout_seconds: float = 2.0
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:3000",)

    @property
    def serial_enabled(self) -> bool:
        return self.pixhawk_serial is not None

    @property
    def video_enabled(self) -> bool:
        return self.video_url is not None

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
            video_url=_optional_text(environ.get("VIDEO_URL")),
            model_path=Path(_text(environ, "MODEL_PATH", str(defaults.model_path))),
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
