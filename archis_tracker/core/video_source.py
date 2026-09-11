"""Timestamp-aware imported video source for evaluator benchmark files."""
from __future__ import annotations

from pathlib import Path

import cv2


class VideoSourceError(ValueError):
    pass


class VideoSource:
    def __init__(self, path: str):
        self.path = Path(path)
        self.capture = cv2.VideoCapture(str(self.path))
        if not self.capture.isOpened():
            raise VideoSourceError(f"Could not open video: {self.path.name}")
        source_fps = float(self.capture.get(cv2.CAP_PROP_FPS))
        self.fps = source_fps if source_fps > 0 else 30.0
        self.frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def frame_index(self) -> int:
        return max(0, int(self.capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1)

    @property
    def progress(self) -> float:
        if self.frame_count <= 0:
            return 0.0
        return min(1.0, (self.frame_index + 1) / self.frame_count)

    def read(self):
        ok, frame = self.capture.read()
        return frame if ok else None

    def rewind(self):
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def close(self):
        self.capture.release()

