"""Segmentation task queue and persistence."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
from typing import Any, Deque, Dict, Iterable, List, Optional

from vidsynth.core import Clip, load_config
from vidsynth.segment import segment_video

from .events import EventBroadcaster
from .workspace import SEGMENTATION_DIR, VIDEOS_DIR, ensure_workspace_layout


@dataclass(slots=True)
class TaskStatus:
    video_id: str
    status: str
    progress: float
    message: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "updated_at": self.updated_at,
        }


class TaskManager:
    """Single-worker queue for segmentation tasks."""

    def __init__(self, broadcaster: EventBroadcaster) -> None:
        self._lock = threading.Lock()
        self._queue: Deque[str] = deque()
        self._active: Optional[str] = None
        self._broadcaster = broadcaster
        self._config = load_config()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        ensure_workspace_layout()
        self._load_queue_state()
        self._worker.start()

    def enqueue(self, video_ids: Iterable[str], *, force: bool = False) -> Dict[str, Any]:
        ensure_workspace_layout()
        queued: List[str] = []
        cached: List[str] = []
        skipped: List[str] = []
        with self._lock:
            for video_id in video_ids:
                if not self._resolve_video_path(video_id):
                    skipped.append(video_id)
                    continue
                if force:
                    self._clear_artifacts(video_id)
                elif self._clips_path(video_id).exists():
                    cached.append(video_id)
                    self._write_status(video_id, status="cached", progress=1.0, message="cached")
                    continue
                if video_id == self._active or video_id in self._queue:
                    skipped.append(video_id)
                    continue
                self._queue.append(video_id)
                queued.append(video_id)
                self._write_status(video_id, status="queued", progress=0.0, message="")
            self._persist_queue()
        for video_id in queued:
            self._publish_status(video_id)
        for video_id in cached:
            self._publish_status(video_id)
        return {
            "queued": queued,
            "cached": cached,
            "skipped": skipped,
            "active": self._active,
            "pending": list(self._queue),
        }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            pending = list(self._queue)
            active = self._active
        statuses: Dict[str, Any] = {}
        for path in SEGMENTATION_DIR.glob("*/status.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            video_id = payload.get("video_id")
            if video_id:
                statuses[video_id] = payload
        return {"queue": {"pending": pending, "active": active}, "statuses": statuses}

    def _worker_loop(self) -> None:
        while True:
            video_id = None
            with self._lock:
                if not self._active and self._queue:
                    video_id = self._queue.popleft()
                    self._active = video_id
                    self._persist_queue()
            if not video_id:
                time.sleep(0.5)
                continue
            try:
                self._run_task(video_id)
            finally:
                with self._lock:
                    self._active = None
                    self._persist_queue()

    def _run_task(self, video_id: str) -> None:
        video_path = self._resolve_video_path(video_id)
        if not video_path:
            self._write_status(video_id, status="error", progress=0, message="video not found")
            self._publish_error(video_id, "video not found")
            return

        last_progress = -1.0

        def progress_callback(value: float) -> None:
            nonlocal last_progress
            normalized = max(0.0, min(1.0, float(value)))
            if normalized == last_progress:
                return
            last_progress = normalized
            self._write_status(video_id, status="running", progress=normalized, message="")
            self._publish_status(video_id)

        self._write_status(video_id, status="running", progress=0.0, message="")
        self._publish_status(video_id)
        try:
            result = segment_video(
                video_id=video_id,
                video_path=video_path,
                config=self._config,
                progress_callback=progress_callback,
            )
            self._write_clips(video_id, result.clips)
            self._write_status(video_id, status="done", progress=1.0, message="")
            self._publish_status(video_id)
        except Exception as exc:
            message = str(exc)
            self._write_status(video_id, status="error", progress=0.0, message=message)
            self._publish_status(video_id)

    def _resolve_video_path(self, video_id: str) -> Optional[Path]:
        for path in VIDEOS_DIR.iterdir():
            if path.is_file() and path.stem == video_id:
                return path
        return None

    def _segmentation_dir(self, video_id: str) -> Path:
        return SEGMENTATION_DIR / video_id

    def _status_path(self, video_id: str) -> Path:
        return self._segmentation_dir(video_id) / "status.json"

    def _clips_path(self, video_id: str) -> Path:
        return self._segmentation_dir(video_id) / "clips.json"

    def _clear_artifacts(self, video_id: str) -> None:
        seg_dir = self._segmentation_dir(video_id)
        if not seg_dir.exists():
            return
        for name in ("clips.json", "status.json"):
            target = seg_dir / name
            if target.exists():
                target.unlink()

    def _write_status(self, video_id: str, *, status: str, progress: float, message: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        normalized = max(0.0, min(1.0, float(progress)))
        payload = TaskStatus(
            video_id=video_id,
            status=status,
            progress=normalized,
            message=message,
            updated_at=now,
        ).to_dict()
        path = self._status_path(video_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_json(path, payload)

    def _write_clips(self, video_id: str, clips: List[Clip]) -> None:
        path = self._clips_path(video_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [clip.to_dict() for clip in clips]
        self._atomic_write_json(path, payload)

    def _persist_queue(self) -> None:
        payload = {"pending": list(self._queue), "active": self._active, "updated_at": self._now()}
        path = SEGMENTATION_DIR / "queue.json"
        self._atomic_write_json(path, payload)

    def _load_queue_state(self) -> None:
        path = SEGMENTATION_DIR / "queue.json"
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        pending = payload.get("pending") or []
        active = payload.get("active")
        self._queue = deque([vid for vid in pending if isinstance(vid, str)])
        if isinstance(active, str):
            self._queue.appendleft(active)
            self._active = None
        self._persist_queue()

    def _publish_status(self, video_id: str) -> None:
        status = self._read_status(video_id)
        if not status:
            return
        self._broadcaster.publish(self._status_to_event(status))

    def _read_status(self, video_id: str) -> Optional[Dict[str, Any]]:
        path = self._status_path(video_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def format_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._status_to_event(payload)

    @staticmethod
    def _status_to_event(payload: Dict[str, Any]) -> Dict[str, Any]:
        video_id = payload.get("video_id")
        status = payload.get("status")
        result_path = None
        if status in {"done", "cached"} and video_id:
            result_path = f"segmentation/{video_id}/clips.json"
        return {
            "stage": "segment",
            "video_id": video_id,
            "status": status,
            "progress": payload.get("progress"),
            "message": payload.get("message"),
            "result_path": result_path,
        }

    @staticmethod
    def _atomic_write_json(path: Path, payload: Dict[str, Any] | List[Any]) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
