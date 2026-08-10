from pathlib import Path

import pytest

from backend.app.config import ConfigError, Settings


def test_defaults_are_local_and_use_repo_model():
    settings = Settings.from_env({})
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.pixhawk_baud == 115200
    assert settings.model_path == Path("model/best.pt")
    assert settings.cors_origins == ("http://127.0.0.1:3000",)


def test_serial_port_is_required_for_ready_runtime():
    settings = Settings.from_env({})
    assert settings.pixhawk_serial is None
    assert settings.serial_enabled is False


def test_invalid_numeric_settings_are_rejected():
    with pytest.raises(ConfigError, match="PIXHAWK_BAUD"):
        Settings.from_env({"PIXHAWK_BAUD": "not-a-number"})


def test_non_finite_float_settings_are_rejected():
    with pytest.raises(ConfigError, match="MAX_FPS"):
        Settings.from_env({"MAX_FPS": "nan"})


def test_environment_values_are_parsed_and_trimmed():
    settings = Settings.from_env(
        {
            "HOST": "127.0.0.1",
            "PORT": "8123",
            "PIXHAWK_SERIAL": " COM7 ",
            "PIXHAWK_BAUD": "57600",
            "VIDEO_URL": " rtsp://camera/stream ",
            "MODEL_PATH": "custom.pt",
            "CORS_ORIGINS": "http://localhost:3000, http://127.0.0.1:3000",
        }
    )
    assert settings.port == 8123
    assert settings.pixhawk_serial == "COM7"
    assert settings.pixhawk_baud == 57600
    assert settings.video_url == "rtsp://camera/stream"
    assert settings.model_path == Path("custom.pt")
    assert settings.cors_origins == (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
