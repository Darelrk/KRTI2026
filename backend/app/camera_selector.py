from __future__ import annotations

from typing import Protocol

from .contracts import CameraId


class HardwareSwitcher(Protocol):
    """Adapter for the transmitter's physical camera-select mechanism.

    The implementation may later send a Pixhawk/Hello Radio command, a serial
    byte sequence, or another device-specific signal. The backend deliberately
    knows only the logical camera id.
    """

    async def select(self, camera: CameraId) -> None:
        """Select ``camera`` on the transmitter or raise on failure."""
