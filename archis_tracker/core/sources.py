"""Native-resolution video, image and image-sequence frame sources."""
from __future__ import annotations

from pathlib import Path
import re

import cv2

from .contracts import FramePacket


class FrameSourceError(ValueError):
    pass


class VideoFrameSource:
    def __init__(self, path: str | Path, fallback_fps: float = 30.0) -> None:
        if fallback_fps <= 0:
            raise FrameSourceError("fallback fps must be positive")
        self.path = Path(path)
        self.capture = cv2.VideoCapture(str(self.path))
        if not self.capture.isOpened():
            raise FrameSourceError(f"could not open video: {self.path}")
        fps = float(self.capture.get(cv2.CAP_PROP_FPS))
        self.fps = fps if fps > 0 else fallback_fps
        self.index = 0

    def read(self) -> FramePacket | None:
        ok, image = self.capture.read()
        if not ok:
            return None
        packet = FramePacket(
            self.index, self.index / self.fps, image, "video",
            {"path": self.path.as_posix()},
        )
        self.index += 1
        return packet

    def close(self) -> None:
        self.capture.release()


class ImageSequenceSource:
    def __init__(self, path: str | Path, fps: float = 30.0) -> None:
        if fps <= 0:
            raise FrameSourceError("fps must be positive")
        source = Path(path)
        if source.is_file():
            self.files = [source]
        elif source.is_dir():
            self.files = sorted((
                item for item in source.iterdir()
                if item.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
            ), key=_natural_key)
        else:
            raise FrameSourceError(f"image source does not exist: {source}")
        if not self.files:
            raise FrameSourceError("image source contains no supported images")
        self.fps = fps
        self.index = 0

    def read(self) -> FramePacket | None:
        if self.index >= len(self.files):
            return None
        path = self.files[self.index]
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise FrameSourceError(f"could not decode image: {path}")
        packet = FramePacket(
            self.index, self.index / self.fps, image, "images",
            {"path": path.as_posix()},
        )
        self.index += 1
        return packet

    def close(self) -> None:
        return None


def open_frame_source(path: str | Path, fps: float = 30.0):
    source = Path(path)
    if source.is_dir() or source.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        return ImageSequenceSource(source, fps)
    return VideoFrameSource(source, fps)


def _natural_key(path: Path) -> tuple[object, ...]:
    return tuple(int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name))
