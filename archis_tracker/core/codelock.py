"""Temporal optical-code verification for beacon identity and decoy rejection."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math

import cv2
import numpy as np

from .contracts import Detection


@dataclass(slots=True)
class _History:
    track_id: int
    x: float
    y: float
    last_frame: int
    samples: deque[tuple[int, float]] = field(default_factory=deque)


class CodeLock:
    def __init__(self, pattern: str, *, symbol_frames: int = 1,
                 minimum_correlation: float = 0.70, association_radius_px: float = 100.0) -> None:
        if len(pattern) < 7 or set(pattern) != {"0", "1"}:
            raise ValueError("CodeLock pattern must contain 0 and 1 and be at least seven bits")
        if symbol_frames < 1:
            raise ValueError("CodeLock symbol_frames must be at least one")
        if not 0.0 <= minimum_correlation <= 1.0:
            raise ValueError("CodeLock minimum_correlation must be between zero and one")
        if association_radius_px <= 0:
            raise ValueError("CodeLock association_radius_px must be positive")
        self.pattern = tuple(int(bit) for bit in pattern for _ in range(symbol_frames))
        self.minimum_correlation = minimum_correlation
        self.association_radius_px = association_radius_px
        self.histories: list[_History] = []
        self.next_id = 1
        self.status = "SEARCHING"
        self.best_correlation: float | None = None

    def reset(self) -> None:
        self.histories.clear()
        self.next_id = 1
        self.status = "SEARCHING"
        self.best_correlation = None

    def filter(self, image: np.ndarray, detections: tuple[Detection, ...], frame_index: int) -> tuple[Detection, ...]:
        self.histories = [item for item in self.histories if frame_index - item.last_frame <= len(self.pattern) * 2]
        unused = set(range(len(self.histories)))
        matched: list[tuple[Detection, _History, float | None]] = []
        for detection in detections:
            choices = [(math.hypot(detection.x_px - self.histories[i].x, detection.y_px - self.histories[i].y), i) for i in unused]
            distance, index = min(choices, default=(math.inf, -1))
            if distance <= self.association_radius_px:
                unused.remove(index)
                history = self.histories[index]
            else:
                history = _History(self.next_id, detection.x_px, detection.y_px, frame_index, deque(maxlen=len(self.pattern) * 2))
                self.next_id += 1
                self.histories.append(history)
            history.x, history.y, history.last_frame = detection.x_px, detection.y_px, frame_index
            history.samples.append((frame_index, _signal(image, detection)))
            correlation = self._correlation(history.samples)
            matched.append((detection, history, correlation))
        valid = [item for item in matched if item[2] is not None and item[2] >= self.minimum_correlation]
        self.best_correlation = max((item[2] for item in matched if item[2] is not None), default=None)
        self.status = "VERIFIED" if valid else ("COLLECTING" if matched else "SEARCHING")
        return tuple(
            Detection(item.x_px, item.y_px, min(1.0, 0.6 * item.confidence + 0.4 * float(corr)),
                      item.width_px, item.height_px, item.algorithm, item.ai_score, float(corr))
            for item, _, corr in sorted(valid, key=lambda value: float(value[2]), reverse=True)
        )

    def _correlation(self, samples: deque[tuple[int, float]]) -> float | None:
        if len(samples) < len(self.pattern):
            return None
        recent = tuple(samples)
        observed = np.asarray([value for _, value in recent], dtype=np.float64)
        observed -= observed.mean()
        norm = float(np.linalg.norm(observed))
        if norm < 1e-6:
            return None
        best = -1.0
        for phase in range(len(self.pattern)):
            expected = np.asarray([self.pattern[(index + phase) % len(self.pattern)] for index, _ in recent], dtype=np.float64)
            expected -= expected.mean()
            denominator = norm * float(np.linalg.norm(expected))
            if denominator > 1e-6:
                best = max(best, float(np.dot(observed, expected) / denominator))
        return best


def _signal(image: np.ndarray, detection: Detection) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    patch = cv2.getRectSubPix(gray.astype(np.float32), (15, 15), (detection.x_px, detection.y_px))
    inner = patch[4:11, 4:11]
    ring = np.concatenate((patch[:3].ravel(), patch[-3:].ravel(), patch[:, :3].ravel(), patch[:, -3:].ravel()))
    return max(0.0, float(np.percentile(inner, 85) - np.median(ring)))
