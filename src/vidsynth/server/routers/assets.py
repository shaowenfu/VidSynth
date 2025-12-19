"""Asset scan and import endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import shutil

import cv2
from fastapi import APIRouter, File, UploadFile

from ..workspace import (
    GT_DIR,
    SEGMENTATION_DIR,
    THUMBNAILS_DIR,
    VIDEOS_DIR,
    ensure_workspace_layout,
)

router = APIRouter(prefix="/api", tags=["assets"])


def _safe_filename(name: str | None) -> str:
    if not name:
        return ""
    return Path(name).name


def _video_files() -> List[Path]:
    if not VIDEOS_DIR.exists():
        return []
    return sorted(
        [
            path
            for path in VIDEOS_DIR.iterdir()
            if path.is_file() and not path.name.startswith(".") and path.name != ".keep"
        ]
    )


def _probe_duration_seconds(video_path: Path) -> float:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return 0.0
    try:
        fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        if fps <= 0:
            return 0.0
        return float(frame_count / fps)
    finally:
        capture.release()


def _ensure_thumbnail(video_path: Path, video_id: str) -> Path | None:
    thumb_path = THUMBNAILS_DIR / f"{video_id}.jpg"
    if thumb_path.exists():
        return thumb_path

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return None
    try:
        success, frame = capture.read()
    finally:
        capture.release()

    if not success:
        return None
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    if cv2.imwrite(str(thumb_path), frame):
        return thumb_path
    return None


def _asset_payload(video_path: Path) -> Dict[str, Any]:
    video_id = video_path.stem
    gt_path = GT_DIR / f"{video_id}.json"
    clips_path = SEGMENTATION_DIR / video_id / "clips.json"
    status_path = SEGMENTATION_DIR / video_id / "status.json"

    thumb_path = _ensure_thumbnail(video_path, video_id)
    duration = _probe_duration_seconds(video_path)
    status_payload: Dict[str, Any] = {}
    if status_path.exists():
        try:
            status_payload = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            status_payload = {}

    raw_status = status_payload.get("status")
    status = raw_status or ("ready" if clips_path.exists() else "idle")
    if status == "done":
        status = "ready"

    payload = {
        "id": video_id,
        "name": video_path.name,
        "duration": duration,
        "hasGT": gt_path.exists(),
        "segmented": clips_path.exists(),
        "video_url": f"/static/videos/{video_path.name}",
        "thumb_url": f"/static/thumbnails/{thumb_path.name}" if thumb_path else None,
        "gt_url": f"/static/gt/{video_id}.json" if gt_path.exists() else None,
        "clips_url": f"/static/segmentation/{video_id}/clips.json" if clips_path.exists() else None,
        "status": status,
        "progress": status_payload.get("progress"),
    }
    return payload


def _list_assets() -> List[Dict[str, Any]]:
    ensure_workspace_layout()
    return [_asset_payload(path) for path in _video_files()]


@router.get("/assets")
def list_assets() -> List[Dict[str, Any]]:
    """Return workspace asset list."""

    return _list_assets()


@router.post("/import/videos")
async def import_videos(files: List[UploadFile] = File(...)) -> List[Dict[str, Any]]:
    """Receive uploaded videos and write into workspace."""

    ensure_workspace_layout()
    for upload in files:
        filename = _safe_filename(upload.filename)
        if not filename:
            continue
        destination = VIDEOS_DIR / filename
        with destination.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        upload.file.close()
        _ensure_thumbnail(destination, destination.stem)
    return _list_assets()
