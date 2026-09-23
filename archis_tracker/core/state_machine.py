"""Explicit acquisition, tracking, coast and reacquisition state machine."""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import CanonicalTrackingState


@dataclass(frozen=True, slots=True)
class StateMachineConfig:
    confirmation_frames: int = 3
    missed_frame_tolerance: int = 1
    coast_timeout_s: float = 0.4
    local_reacquire_timeout_s: float = 0.6


class TrackingStateMachine:
    def __init__(self, config: StateMachineConfig | None = None) -> None:
        self.config = config or StateMachineConfig()
        self.reset()

    def reset(self) -> None:
        self.state = CanonicalTrackingState.SEARCH
        self.state_elapsed_s = 0.0
        self.confirmation_count = 0
        self.missed_frames = 0

    @property
    def use_prediction_gate(self) -> bool:
        return (
            self.state in {CanonicalTrackingState.TRACK, CanonicalTrackingState.COAST}
            or (
                self.state == CanonicalTrackingState.REACQUIRE
                and self.state_elapsed_s < self.config.local_reacquire_timeout_s
            )
        )

    @property
    def search_scope(self) -> str:
        if self.state == CanonicalTrackingState.REACQUIRE:
            return "local" if self.state_elapsed_s < self.config.local_reacquire_timeout_s else "global"
        return "full" if not self.use_prediction_gate else "local"

    def update(self, detected: bool, dt: float) -> CanonicalTrackingState:
        if dt <= 0:
            raise ValueError("state-machine dt must be positive")
        self.state_elapsed_s += dt

        if self.state in {CanonicalTrackingState.SEARCH, CanonicalTrackingState.REACQUIRE}:
            if detected:
                self.state = CanonicalTrackingState.ACQUIRE
                self.state_elapsed_s = 0.0
                self.confirmation_count = 1
                self.missed_frames = 0
            return self.state

        if self.state == CanonicalTrackingState.ACQUIRE:
            if detected:
                self.confirmation_count += 1
                self.missed_frames = 0
                if self.confirmation_count >= self.config.confirmation_frames:
                    self.state = CanonicalTrackingState.TRACK
                    self.state_elapsed_s = 0.0
            else:
                self.missed_frames += 1
                if self.missed_frames > self.config.missed_frame_tolerance:
                    self.state = CanonicalTrackingState.SEARCH
                    self.state_elapsed_s = 0.0
                    self.confirmation_count = 0
            return self.state

        if self.state == CanonicalTrackingState.TRACK:
            if not detected:
                self.state = CanonicalTrackingState.COAST
                self.state_elapsed_s = 0.0
            return self.state

        if self.state == CanonicalTrackingState.COAST:
            if detected:
                self.state = CanonicalTrackingState.TRACK
                self.state_elapsed_s = 0.0
            elif self.state_elapsed_s >= self.config.coast_timeout_s:
                self.state = CanonicalTrackingState.REACQUIRE
                self.state_elapsed_s = 0.0
            return self.state

        return self.state
