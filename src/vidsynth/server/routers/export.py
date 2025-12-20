"""Export endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..state import export_task_manager
from ..workspace import EXPORTS_DIR, ensure_workspace_layout

router = APIRouter(prefix="/api", tags=["export"])


class ExportRequest(BaseModel):
    theme: str = Field(..., min_length=1)
    theme_slug: str | None = None
    video_id: str = Field(..., min_length=1)
    edl_path: str | None = None
    source_video_path: str | None = None
    force: bool = False


@router.post("/export")
def export_video(request: ExportRequest) -> Dict[str, Any]:
    ensure_workspace_layout()
    return export_task_manager.enqueue(
        theme=request.theme,
        theme_slug=request.theme_slug,
        video_id=request.video_id,
        force=request.force,
        edl_path=request.edl_path,
        source_video_path=request.source_video_path,
    )


@router.get("/export/{theme_slug}/{video_id}")
def export_status(theme_slug: str, video_id: str) -> Dict[str, Any]:
    ensure_workspace_layout()
    status_path = EXPORTS_DIR / theme_slug / video_id / "status.json"
    output_path = EXPORTS_DIR / theme_slug / video_id / "output.mp4"
    payload: Dict[str, Any] = {}
    if status_path.exists():
        payload = _read_json(status_path)
    else:
        payload = {
            "theme_slug": theme_slug,
            "video_id": video_id,
            "status": "done" if output_path.exists() else "idle",
            "progress": 1.0 if output_path.exists() else 0.0,
            "message": "",
        }
    result_path = None
    if output_path.exists():
        result_path = f"exports/{theme_slug}/{video_id}/output.mp4"
    payload["result_path"] = result_path
    return payload


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="invalid export status") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="invalid export status")
    return data
