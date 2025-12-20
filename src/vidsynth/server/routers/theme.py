"""Theme expansion and matching endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from vidsynth.theme_match import build_theme_query

from ..state import theme_task_manager
from ..workspace import THEMES_DIR, ensure_workspace_layout

router = APIRouter(prefix="/api/theme", tags=["theme"])


class ExpandRequest(BaseModel):
    theme_text: str = Field(..., min_length=1)
    positives: List[str] | None = None
    negatives: List[str] | None = None


class AnalyzeRequest(BaseModel):
    theme: str = Field(..., min_length=1)
    positives: List[str] = Field(default_factory=list)
    negatives: List[str] = Field(default_factory=list)
    video_ids: List[str] = Field(default_factory=list)
    force: bool = False


@router.post("/expand")
def expand_theme(request: ExpandRequest) -> Dict[str, Any]:
    query = build_theme_query(request.theme_text, request.positives, request.negatives)
    return {
        "theme": query.theme,
        "positives": query.positive_texts(),
        "negatives": query.negative_texts(),
    }


@router.post("/analyze")
def analyze_theme(request: AnalyzeRequest) -> Dict[str, Any]:
    ensure_workspace_layout()
    return theme_task_manager.enqueue(
        theme=request.theme,
        positives=request.positives,
        negatives=request.negatives,
        video_ids=request.video_ids,
        force=request.force,
    )


@router.get("/{theme_slug}/result")
def get_theme_result(theme_slug: str) -> Dict[str, Any]:
    ensure_workspace_layout()
    path = THEMES_DIR / theme_slug / "scores.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="scores not found")
    return _read_json(path)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="invalid scores payload") from exc
