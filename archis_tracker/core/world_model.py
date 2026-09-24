"""Explicit two-terminal 3D geometry for the FSOC coarse-alignment scene.

The image generator historically used a 2D angular plane.  This module gives
that plane a physical interpretation without allowing geometric truth to enter
the detector or controller: targets are projected onto a range plane, while
the receiver camera exposes its independently computed boresight and FOV.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable

from .camera import VirtualCamera
from .config import CameraConfig, EnvironmentConfig, TerminalWorldConfig
from .target import TargetBeacon


@dataclass(frozen=True, slots=True)
class Vector3:
    x: float
    y: float
    z: float

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)


@dataclass(frozen=True, slots=True)
class Orientation3D:
    """Right-handed yaw, pitch and roll angles in degrees."""

    yaw_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0


class TerminalRole(Enum):
    RECEIVER = "receiver"
    TRANSMITTER = "transmitter"
    DECOY = "decoy"


@dataclass(frozen=True, slots=True)
class TerminalState:
    terminal_id: str
    role: TerminalRole
    position_m: Vector3
    velocity_m_s: Vector3
    orientation: Orientation3D
    is_designated: bool = False


@dataclass(frozen=True, slots=True)
class CameraFrustum:
    horizontal_fov_deg: float
    vertical_fov_deg: float
    boresight_azimuth_deg: float
    boresight_elevation_deg: float


@dataclass(frozen=True, slots=True)
class WorldGeometrySnapshot:
    receiver: TerminalState
    transmitter: TerminalState
    decoys: tuple[TerminalState, ...]
    camera: CameraFrustum
    separation_m: float
    line_of_sight_azimuth_deg: float
    line_of_sight_elevation_deg: float
    relative_azimuth_deg: float
    relative_elevation_deg: float
    transmitter_in_fov: bool


class TwoTerminalWorldModel:
    """Maps the deterministic angular scene to explicit 3D terminal states."""

    def __init__(
        self,
        camera_config: CameraConfig,
        environment_config: EnvironmentConfig,
        config: TerminalWorldConfig | None = None,
    ) -> None:
        self.camera_config = camera_config
        self.environment_config = environment_config
        self.config = config or TerminalWorldConfig()
        self._elapsed_s = 0.0
        self._previous_positions: dict[str, Vector3] = {}
        self._previous_velocities: dict[str, Vector3] = {}
        self.snapshot: WorldGeometrySnapshot | None = None

    def reset(
        self,
        camera: VirtualCamera,
        primary: TargetBeacon,
        decoys: Iterable[TargetBeacon] = (),
    ) -> WorldGeometrySnapshot:
        self._elapsed_s = 0.0
        self._previous_positions.clear()
        self._previous_velocities.clear()
        return self.update(0.0, camera, primary, decoys)

    def update(
        self,
        dt: float,
        camera: VirtualCamera,
        primary: TargetBeacon,
        decoys: Iterable[TargetBeacon] = (),
    ) -> WorldGeometrySnapshot:
        if dt < 0:
            raise ValueError("world-model dt cannot be negative")
        self._elapsed_s += dt
        receiver_position = self._receiver_position()
        receiver_velocity = Vector3(*map(float, self.config.receiver_velocity_m_s))
        base_yaw, base_pitch, base_roll = map(float, self.config.receiver_orientation_deg)
        boresight_azimuth = base_yaw + self._camera_azimuth(camera)
        boresight_elevation = base_pitch + self._camera_elevation(camera)
        receiver = TerminalState(
            "RX-1",
            TerminalRole.RECEIVER,
            receiver_position,
            receiver_velocity,
            Orientation3D(boresight_azimuth, boresight_elevation, base_roll),
            False,
        )

        transmitter = self._terminal_from_target(primary, receiver_position, dt, TerminalRole.TRANSMITTER)
        decoy_states = tuple(
            self._terminal_from_target(target, receiver_position, dt, TerminalRole.DECOY)
            for target in decoys
        )
        los = transmitter.position_m - receiver.position_m
        separation, azimuth, elevation = self._range_and_angles(los)
        relative_azimuth = self._wrap_degrees(azimuth - boresight_azimuth)
        relative_elevation = elevation - boresight_elevation
        frustum = CameraFrustum(
            self.camera_config.fov_x_deg,
            self.camera_config.fov_y_deg,
            boresight_azimuth,
            boresight_elevation,
        )
        self.snapshot = WorldGeometrySnapshot(
            receiver,
            transmitter,
            decoy_states,
            frustum,
            separation,
            azimuth,
            elevation,
            relative_azimuth,
            relative_elevation,
            abs(relative_azimuth) <= frustum.horizontal_fov_deg / 2.0
            and abs(relative_elevation) <= frustum.vertical_fov_deg / 2.0,
        )
        return self.snapshot

    def _receiver_position(self) -> Vector3:
        px, py, pz = map(float, self.config.receiver_position_m)
        vx, vy, vz = map(float, self.config.receiver_velocity_m_s)
        return Vector3(px + vx * self._elapsed_s, py + vy * self._elapsed_s, pz + vz * self._elapsed_s)

    def _terminal_from_target(
        self,
        target: TargetBeacon,
        receiver_position: Vector3,
        dt: float,
        role: TerminalRole,
    ) -> TerminalState:
        range_m = float(target.config.range_m or self.config.nominal_range_m)
        azimuth = (target.x - self.environment_config.screen_width / 2.0) / self.camera_config.pixels_per_deg_x
        # Image/world Y grows downward, whereas physical elevation grows up.
        elevation = -(target.y - self.environment_config.screen_height / 2.0) / self.camera_config.pixels_per_deg_y
        azimuth_rad = math.radians(azimuth)
        elevation_rad = math.radians(elevation)
        cos_elevation = math.cos(elevation_rad)
        relative = Vector3(
            range_m * cos_elevation * math.sin(azimuth_rad),
            range_m * math.sin(elevation_rad),
            range_m * cos_elevation * math.cos(azimuth_rad),
        )
        position = receiver_position + relative
        terminal_id = f"TX-{target.target_id}"
        previous = self._previous_positions.get(terminal_id)
        receiver_velocity = Vector3(*map(float, self.config.receiver_velocity_m_s))
        if dt <= 0 and terminal_id in self._previous_velocities:
            velocity = self._previous_velocities[terminal_id]
        elif previous is None or dt <= 0:
            # Analytic first-frame approximation from angular target velocity.
            az_rate = math.radians(target.vx / self.camera_config.pixels_per_deg_x)
            el_rate = math.radians(-target.vy / self.camera_config.pixels_per_deg_y)
            velocity = receiver_velocity + Vector3(range_m * az_rate, range_m * el_rate, 0.0)
        else:
            velocity = Vector3(
                (position.x - previous.x) / dt,
                (position.y - previous.y) / dt,
                (position.z - previous.z) / dt,
            )
        self._previous_positions[terminal_id] = position
        self._previous_velocities[terminal_id] = velocity

        if target.config.orientation_deg is None:
            facing = receiver_position - position
            _, facing_azimuth, facing_elevation = self._range_and_angles(facing)
            orientation = Orientation3D(facing_azimuth, facing_elevation, 0.0)
        else:
            orientation = Orientation3D(*map(float, target.config.orientation_deg))
        return TerminalState(
            terminal_id,
            role,
            position,
            velocity,
            orientation,
            target.is_primary,
        )

    def _camera_azimuth(self, camera: VirtualCamera) -> float:
        offset_px = camera.world_x - self.environment_config.screen_width / 2.0
        return offset_px / self.camera_config.pixels_per_deg_x

    def _camera_elevation(self, camera: VirtualCamera) -> float:
        offset_px = camera.world_y - self.environment_config.screen_height / 2.0
        return -offset_px / self.camera_config.pixels_per_deg_y

    @staticmethod
    def _range_and_angles(vector: Vector3) -> tuple[float, float, float]:
        distance = vector.magnitude
        if distance <= 0:
            return 0.0, 0.0, 0.0
        azimuth = math.degrees(math.atan2(vector.x, vector.z))
        elevation = math.degrees(math.atan2(vector.y, math.hypot(vector.x, vector.z)))
        return distance, azimuth, elevation

    @staticmethod
    def _wrap_degrees(angle: float) -> float:
        return (angle + 180.0) % 360.0 - 180.0
