"""Workspace paths and initialization helpers."""

from __future__ import annotations

import os
from pathlib import Path

WORKSPACE_ENV_KEY = "VIDSYNTH_WORKSPACE_ROOT"


def _resolve_workspace_root() -> Path:
    env_value = os.getenv(WORKSPACE_ENV_KEY)
    if env_value:
        return Path(env_value).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "workspace"


WORKSPACE_ROOT = _resolve_workspace_root()
VIDEOS_DIR = WORKSPACE_ROOT / "videos"
GT_DIR = WORKSPACE_ROOT / "gt"
THUMBNAILS_DIR = WORKSPACE_ROOT / "thumbnails"
SEGMENTATION_DIR = WORKSPACE_ROOT / "segmentation"
THEMES_DIR = WORKSPACE_ROOT / "themes"


def ensure_workspace_layout() -> None:
    """Ensure workspace directories exist."""

    for path in (
        WORKSPACE_ROOT,
        VIDEOS_DIR,
        GT_DIR,
        THUMBNAILS_DIR,
        SEGMENTATION_DIR,
        THEMES_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
