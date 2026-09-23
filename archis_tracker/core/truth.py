"""Ground-truth sidecars for evaluator-supplied recordings."""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import GroundTruthSample


class TruthSidecarError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _TruthRow:
    frame_index: int | None
    timestamp_s: float | None
    sample: GroundTruthSample


class TruthSidecar:
    def __init__(self, rows: list[_TruthRow]) -> None:
        if not rows:
            raise TruthSidecarError("truth sidecar contains no rows")
        frame_ids = [row.frame_index for row in rows if row.frame_index is not None]
        timestamps = [row.timestamp_s for row in rows if row.timestamp_s is not None]
        if len(frame_ids) != len(set(frame_ids)):
            raise TruthSidecarError("truth sidecar contains duplicate frame_index values")
        if len(timestamps) != len(set(timestamps)):
            raise TruthSidecarError("truth sidecar contains duplicate timestamp_s values")
        self._by_frame = {row.frame_index: row.sample for row in rows if row.frame_index is not None}
        self._timed = sorted(
            ((row.timestamp_s, row.sample) for row in rows if row.timestamp_s is not None),
            key=lambda item: item[0],
        )

    @classmethod
    def load(cls, path: str | Path) -> "TruthSidecar":
        source = Path(path)
        try:
            if source.suffix.lower() == ".csv":
                with source.open(newline="", encoding="utf-8-sig") as handle:
                    records = list(csv.DictReader(handle))
            elif source.suffix.lower() == ".json":
                payload = json.loads(source.read_text(encoding="utf-8"))
                records = payload.get("frames") if isinstance(payload, dict) else payload
            else:
                raise TruthSidecarError("truth sidecar must be CSV or JSON")
        except (OSError, json.JSONDecodeError, csv.Error) as exc:
            raise TruthSidecarError(f"could not read truth sidecar: {exc}") from exc
        if not isinstance(records, list):
            raise TruthSidecarError("JSON truth must be an array or contain a frames array")
        return cls([_parse_row(record, index) for index, record in enumerate(records)])

    def sample_for(
        self, frame_index: int, timestamp_s: float, *, interpolate: bool = False
    ) -> GroundTruthSample | None:
        if frame_index in self._by_frame:
            return self._by_frame[frame_index]
        exact = next((sample for stamp, sample in self._timed if abs(stamp - timestamp_s) <= 1e-6), None)
        if exact is not None or not interpolate or len(self._timed) < 2:
            return exact
        before = [(stamp, sample) for stamp, sample in self._timed if stamp <= timestamp_s]
        after = [(stamp, sample) for stamp, sample in self._timed if stamp >= timestamp_s]
        if not before or not after:
            return None
        left_t, left = before[-1]
        right_t, right = after[0]
        if left_t == right_t or left.target_id != right.target_id or not (left.visible and right.visible):
            return left if left_t == timestamp_s else None
        ratio = (timestamp_s - left_t) / (right_t - left_t)
        return GroundTruthSample(
            left.x_px + ratio * (right.x_px - left.x_px),
            left.y_px + ratio * (right.y_px - left.y_px),
            True,
            left.target_id,
        )


def _parse_row(record: Any, row_index: int) -> _TruthRow:
    if not isinstance(record, dict):
        raise TruthSidecarError(f"truth row {row_index + 1} must be an object")
    try:
        frame = record.get("frame_index")
        stamp = record.get("timestamp_s")
        if frame in (None, "") and stamp in (None, ""):
            raise TruthSidecarError(f"truth row {row_index + 1} needs frame_index or timestamp_s")
        frame_index = None if frame in (None, "") else int(frame)
        timestamp_s = None if stamp in (None, "") else float(stamp)
        x_px, y_px = float(record["x_px"]), float(record["y_px"])
        raw_visible = record.get("visible", True)
        if isinstance(raw_visible, bool):
            visible = raw_visible
        else:
            normalized = str(raw_visible).strip().lower()
            if normalized not in {"0", "1", "false", "true", "no", "yes"}:
                raise ValueError("visible must be true/false, yes/no, or 1/0")
            visible = normalized in {"1", "true", "yes"}
        target_id = str(record.get("target_id") or "primary")
    except (KeyError, TypeError, ValueError) as exc:
        raise TruthSidecarError(f"invalid truth row {row_index + 1}: {exc}") from exc
    if frame_index is not None and frame_index < 0:
        raise TruthSidecarError("frame_index cannot be negative")
    if timestamp_s is not None and timestamp_s < 0:
        raise TruthSidecarError("timestamp_s cannot be negative")
    if not all(math.isfinite(value) for value in (x_px, y_px)):
        raise TruthSidecarError("truth coordinates must be finite")
    if timestamp_s is not None and not math.isfinite(timestamp_s):
        raise TruthSidecarError("timestamp_s must be finite")
    return _TruthRow(frame_index, timestamp_s, GroundTruthSample(x_px, y_px, visible, target_id))
