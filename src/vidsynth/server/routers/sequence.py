"""Sequencing endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..state import sequence_task_manager
from ..workspace import EDL_DIR, ensure_workspace_layout

router = APIRouter(prefix="/api", tags=["sequence"])


class SequenceParams(BaseModel):
    upper_threshold: float = Field(0.2, ge=0.0)
    lower_threshold: float | None = None
    min_duration: float | None = None
    max_duration: float | None = None
    merge_gap: float | None = None


class SequenceRequest(BaseModel):
    theme: str = Field(..., min_length=1)
    theme_slug: str | None = None
    params: SequenceParams = Field(default_factory=SequenceParams)
    force: bool = False
    video_ids: List[str] = Field(default_factory=list)


@router.post("/sequence")
def run_sequence(request: SequenceRequest) -> Dict[str, Any]:
    ensure_workspace_layout()
    return sequence_task_manager.enqueue(
        theme=request.theme,
        theme_slug=request.theme_slug,
        video_ids=request.video_ids,
        force=request.force,
        threshold_upper=request.params.upper_threshold,
        threshold_lower=request.params.lower_threshold if request.params.lower_threshold is not None else request.params.upper_threshold,
        min_seconds=request.params.min_duration,
        max_seconds=request.params.max_duration,
        merge_gap=request.params.merge_gap,
    )


@router.get("/sequence/{theme_slug}/edl")
def get_edl(theme_slug: str) -> List[Dict[str, Any]]:
    ensure_workspace_layout()
    path = EDL_DIR / theme_slug / "edl.json"
    return _format_edl_response(path, fallback_video_id=None)


@router.get("/sequence/{theme_slug}/status")
def get_sequence_status(theme_slug: str) -> Dict[str, Any]:
    ensure_workspace_layout()
    path = EDL_DIR / theme_slug / "status.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="status not found")
    return _read_json_dict(path)


@router.get("/sequence/{theme_slug}/{video_id}/edl")
def get_edl_legacy(theme_slug: str, video_id: str) -> List[Dict[str, Any]]:
    ensure_workspace_layout()
    path = EDL_DIR / theme_slug / "edl.json"
    return _format_edl_response(path, fallback_video_id=video_id)


def _read_json_list(path: Path) -> List[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="invalid edl payload") from exc
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="invalid edl payload")
    cleaned: List[Dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            cleaned.append(item)
    return cleaned


def _read_json_dict(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="invalid status payload") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="invalid status payload")
    return data


def _format_edl_response(path: Path, fallback_video_id: str | None) -> List[Dict[str, Any]]:
    if not path.exists():
        raise HTTPException(status_code=404, detail="edl not found")
    payload = _read_json_list(path)
    items: List[Dict[str, Any]] = []
    for idx, entry in enumerate(payload, start=1):
        try:
            t_start = float(entry.get("t_start", 0.0))
            t_end = float(entry.get("t_end", 0.0))
        except (TypeError, ValueError):
            continue
        source_video_id = str(entry.get("video_id") or fallback_video_id or "")
        items.append(
            {
                "index": idx,
                "source_video_id": source_video_id,
                "t_start": t_start,
                "t_end": t_end,
                "duration": max(0.0, t_end - t_start),
                "reason": str(entry.get("reason", "")),
                "clip_id": entry.get("clip_id"),
                "thumb_url": entry.get("thumb_url"),
                "score": entry.get("score"),
            }
        )
    return items
