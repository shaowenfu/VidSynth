"""Segmentation endpoints and SSE stream."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..events import stream_events
from ..state import broadcaster, task_manager

router = APIRouter(prefix="/api", tags=["segmentation"])


class SegmentRequest(BaseModel):
    video_ids: List[str] = Field(default_factory=list)
    force: bool = False


@router.post("/segment")
def segment_videos(request: SegmentRequest) -> Dict[str, Any]:
    """Queue segmentation tasks for the provided video ids."""

    return task_manager.enqueue(request.video_ids, force=request.force)


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    """SSE channel for task progress."""

    snapshot = task_manager.snapshot()
    initial_messages = [{"type": "snapshot", "payload": snapshot}]
    generator = stream_events(request, broadcaster, initial_messages=initial_messages)
    return StreamingResponse(generator, media_type="text/event-stream")
