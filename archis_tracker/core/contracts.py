"""Immutable contracts shared by simulation, tracking, UI and evaluation.

Ground truth deliberately lives beside a frame rather than inside detector input.
Only evaluation code receives :class:`GroundTruthSample`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence


class CanonicalTrackingState(StrEnum):
    SEARCH = "search"
    ACQUIRE = "acquire"
    TRACK = "track"
    COAST = "coast"
    REACQUIRE = "reacquire"


@dataclass(frozen=True, slots=True)
class FramePacket:
    index: int
    timestamp_s: float
    image: Any
    source: str = "simulation"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.index < 0 or self.timestamp_s < 0:
            raise ValueError("frame index and timestamp must be non-negative")
        if hasattr(self.image, "setflags"):
            self.image.setflags(write=False)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class GroundTruthSample:
    x_px: float
    y_px: float
    visible: bool = True
    target_id: str = "primary"


@dataclass(frozen=True, slots=True)
class Detection:
    x_px: float
    y_px: float
    confidence: float
    width_px: float
    height_px: float
    algorithm: str = "classical"
    ai_score: float | None = None
    identity_score: float | None = None
    fwhm_px: float | None = None
    snr_aperture: float | None = None
    snr_peak: float | None = None
    clipped: bool = False
    saturated_fraction: float = 0.0


@dataclass(frozen=True, slots=True)
class TrackEstimate:
    x_px: float
    y_px: float
    velocity_x_px_s: float
    velocity_y_px_s: float
    covariance: tuple[tuple[float, ...], ...]
    confidence: float
    state: CanonicalTrackingState


@dataclass(frozen=True, slots=True)
class CameraCommand:
    pan_rate_deg_s: float
    tilt_rate_deg_s: float


@dataclass(frozen=True, slots=True)
class TrackingResult:
    frame: FramePacket
    state: CanonicalTrackingState
    detections: tuple[Detection, ...]
    selected: Detection | None
    estimate: TrackEstimate | None
    command: CameraCommand | None
    processing_time_ms: float
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.processing_time_ms < 0:
            raise ValueError("processing time cannot be negative")
        object.__setattr__(self, "diagnostics", MappingProxyType(dict(self.diagnostics)))


class FrameSource(Protocol):
    def read(self) -> FramePacket | None: ...
    def close(self) -> None: ...


class Detector(Protocol):
    def detect(self, frame: FramePacket) -> Sequence[Detection]: ...
