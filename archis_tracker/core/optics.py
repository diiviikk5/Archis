"""Pinhole-camera geometry for FSOC angular performance reporting.

The tracker operates in sensor pixels because that is what the SIH gates use.
This module provides the physically meaningful conversion to angular separation
without changing detection, association, or control behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class PinholeCameraModel:
    width_px: int
    height_px: int
    horizontal_fov_deg: float
    vertical_fov_deg: float

    def __post_init__(self) -> None:
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("camera dimensions must be positive")
        if not 0.0 < self.horizontal_fov_deg < 180.0:
            raise ValueError("horizontal FOV must be between 0 and 180 degrees")
        if not 0.0 < self.vertical_fov_deg < 180.0:
            raise ValueError("vertical FOV must be between 0 and 180 degrees")

    @property
    def fx_px(self) -> float:
        return self.width_px / (2.0 * math.tan(math.radians(self.horizontal_fov_deg) / 2.0))

    @property
    def fy_px(self) -> float:
        return self.height_px / (2.0 * math.tan(math.radians(self.vertical_fov_deg) / 2.0))

    @property
    def principal_point_px(self) -> tuple[float, float]:
        return self.width_px / 2.0, self.height_px / 2.0

    def ray(self, x_px: float, y_px: float) -> tuple[float, float, float]:
        """Return a unit camera-frame ray where +x is right and +y is up."""
        cx, cy = self.principal_point_px
        x = (float(x_px) - cx) / self.fx_px
        y = (cy - float(y_px)) / self.fy_px
        norm = math.sqrt(x * x + y * y + 1.0)
        return x / norm, y / norm, 1.0 / norm

    def angular_separation_rad(
        self, first_px: tuple[float, float], second_px: tuple[float, float]
    ) -> float:
        """Great-circle separation between two sensor rays in radians."""
        first = self.ray(*first_px)
        second = self.ray(*second_px)
        cross_x = first[1] * second[2] - first[2] * second[1]
        cross_y = first[2] * second[0] - first[0] * second[2]
        cross_z = first[0] * second[1] - first[1] * second[0]
        cross_norm = math.sqrt(cross_x * cross_x + cross_y * cross_y + cross_z * cross_z)
        dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(first, second))))
        return math.atan2(cross_norm, dot)

    def angular_separation_urad(
        self, first_px: tuple[float, float], second_px: tuple[float, float]
    ) -> float:
        return self.angular_separation_rad(first_px, second_px) * 1_000_000.0

    def boresight_offset_urad(self, x_px: float, y_px: float) -> float:
        return self.angular_separation_urad((x_px, y_px), self.principal_point_px)
