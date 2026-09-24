"""Packaged-resource and writable application-data locations."""
from __future__ import annotations

import os
from pathlib import Path
import sys


def resource_path(relative: str | Path) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / relative


def user_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "ArchisTracker"
    path.mkdir(parents=True, exist_ok=True)
    return path
