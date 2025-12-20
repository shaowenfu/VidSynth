"""Export task queue and SSE status updates."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from typing import Any, Deque, Dict, Optional

from vidsynth.core import load_config
from vidsynth.export import Exporter

from .events import EventBroadcaster
from .workspace import EDL_DIR, EXPORTS_DIR, VIDEOS_DIR, ensure_workspace_layout


@dataclass(slots=True)
class ExportJob:
    theme: str
    theme_slug: str
    video_id: str
    force: bool
    edl_path: Optional[str]
    source_video_path: Optional[str]


@dataclass(slots=True)
class ExportStatus:
    theme: str
    theme_slug: str
    video_id: str
    status: str
    progress: float
    message: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme": self.theme,
            "theme_slug": self.theme_slug,
            "video_id": self.video_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "updated_at": self.updated_at,
        }


class ExportTaskManager:
    """Single-worker queue for export tasks."""

    def __init__(self, broadcaster: EventBroadcaster) -> None:
        self._lock = threading.Lock()
        self._queue: Deque[ExportJob] = deque()
        self._active: Optional[ExportJob] = None
        self._broadcaster = broadcaster
        self._config = load_config()
        ensure_workspace_layout()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def enqueue(
        self,
        *,
        theme: str,
        theme_slug: Optional[str],
        video_id: str,
        force: bool,
        edl_path: Optional[str] = None,
        source_video_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        ensure_workspace_layout()
        if not video_id:
            return {"theme": theme, "theme_slug": theme_slug, "status": "skipped", "message": "missing video_id"}
        resolved_slug = theme_slug or _slugify(theme)
        if force:
            self._clear_artifacts(resolved_slug, video_id)
        output_path = self._output_path(resolved_slug, video_id)
        if output_path.exists() and not force:
            self._write_status(
                theme=theme,
                theme_slug=resolved_slug,
                video_id=video_id,
                status="cached",
                progress=1.0,
                message="cached",
            )
            self._publish_status(resolved_slug, video_id)
            return {
                "theme": theme,
                "theme_slug": resolved_slug,
                "video_id": video_id,
                "status": "cached",
                "result_path": f"exports/{resolved_slug}/{video_id}/output.mp4",
            }
        with self._lock:
            if self._active and self._active.theme_slug == resolved_slug and self._active.video_id == video_id:
                return {"theme": theme, "theme_slug": resolved_slug, "video_id": video_id, "status": "skipped"}
            if any(
                job.theme_slug == resolved_slug and job.video_id == video_id for job in self._queue
            ):
                return {"theme": theme, "theme_slug": resolved_slug, "video_id": video_id, "status": "skipped"}
            self._queue.append(
                ExportJob(
                    theme=theme,
                    theme_slug=resolved_slug,
                    video_id=video_id,
                    force=force,
                    edl_path=edl_path,
                    source_video_path=source_video_path,
                )
            )
            self._write_status(
                theme=theme,
                theme_slug=resolved_slug,
                video_id=video_id,
                status="queued",
                progress=0.0,
                message="queued",
            )
        self._publish_status(resolved_slug, video_id)
        return {"theme": theme, "theme_slug": resolved_slug, "video_id": video_id, "status": "queued"}

    def _worker_loop(self) -> None:
        while True:
            job = None
            with self._lock:
                if not self._active and self._queue:
                    job = self._queue.popleft()
                    self._active = job
            if not job:
                time.sleep(0.5)
                continue
            try:
                self._run_job(job)
            finally:
                with self._lock:
                    self._active = None

    def _run_job(self, job: ExportJob) -> None:
        try:
            self._write_status(
                theme=job.theme,
                theme_slug=job.theme_slug,
                video_id=job.video_id,
                status="running",
                progress=0.05,
                message="loading edl",
            )
            self._publish_status(job.theme_slug, job.video_id)
            edl_path = self._resolve_edl_path(job)
            if not edl_path.exists():
                raise FileNotFoundError(f"edl not found: {edl_path}")
            source_video = self._resolve_source_video(job)
            if not source_video:
                raise FileNotFoundError(f"source video not found for {job.video_id}")
            exporter = Exporter(self._config)
            items = exporter.load_edl(edl_path)
            self._write_status(
                theme=job.theme,
                theme_slug=job.theme_slug,
                video_id=job.video_id,
                status="running",
                progress=0.4,
                message="exporting",
            )
            self._publish_status(job.theme_slug, job.video_id)
            output_path = self._output_path(job.theme_slug, job.video_id)
            exporter.export(items, source_video=source_video, output_path=output_path)
            self._write_status(
                theme=job.theme,
                theme_slug=job.theme_slug,
                video_id=job.video_id,
                status="done",
                progress=1.0,
                message="done",
            )
            self._publish_status(job.theme_slug, job.video_id)
        except Exception as exc:
            self._write_status(
                theme=job.theme,
                theme_slug=job.theme_slug,
                video_id=job.video_id,
                status="error",
                progress=0.0,
                message=str(exc),
            )
            self._publish_status(job.theme_slug, job.video_id)

    def _resolve_edl_path(self, job: ExportJob) -> Path:
        if job.edl_path:
            return Path(job.edl_path)
        return EDL_DIR / job.theme_slug / job.video_id / "edl.json"

    def _resolve_source_video(self, job: ExportJob) -> Optional[Path]:
        if job.source_video_path:
            return Path(job.source_video_path)
        if not VIDEOS_DIR.exists():
            return None
        for path in VIDEOS_DIR.iterdir():
            if path.is_file() and path.stem == job.video_id:
                return path
        return None

    def _output_path(self, theme_slug: str, video_id: str) -> Path:
        return EXPORTS_DIR / theme_slug / video_id / "output.mp4"

    def _status_path(self, theme_slug: str, video_id: str) -> Path:
        return EXPORTS_DIR / theme_slug / video_id / "status.json"

    def _clear_artifacts(self, theme_slug: str, video_id: str) -> None:
        output_path = self._output_path(theme_slug, video_id)
        status_path = self._status_path(theme_slug, video_id)
        if output_path.exists():
            output_path.unlink()
        if status_path.exists():
            status_path.unlink()

    def _write_status(
        self,
        *,
        theme: str,
        theme_slug: str,
        video_id: str,
        status: str,
        progress: float,
        message: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        normalized = max(0.0, min(1.0, float(progress)))
        payload = ExportStatus(
            theme=theme,
            theme_slug=theme_slug,
            video_id=video_id,
            status=status,
            progress=normalized,
            message=message,
            updated_at=now,
        ).to_dict()
        path = self._status_path(theme_slug, video_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_json(path, payload)

    def _read_status(self, theme_slug: str, video_id: str) -> Optional[Dict[str, Any]]:
        path = self._status_path(theme_slug, video_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _publish_status(self, theme_slug: str, video_id: str) -> None:
        status = self._read_status(theme_slug, video_id)
        if not status:
            return
        self._broadcaster.publish(self._status_to_event(status))

    @staticmethod
    def _status_to_event(payload: Dict[str, Any]) -> Dict[str, Any]:
        theme = payload.get("theme")
        theme_slug = payload.get("theme_slug")
        video_id = payload.get("video_id")
        status = payload.get("status")
        result_path = None
        if status in {"done", "cached"} and theme_slug and video_id:
            result_path = f"exports/{theme_slug}/{video_id}/output.mp4"
        return {
            "stage": "export",
            "theme": theme,
            "video_id": video_id,
            "status": status,
            "progress": payload.get("progress"),
            "message": payload.get("message"),
            "result_path": result_path,
        }

    @staticmethod
    def _atomic_write_json(path: Path, payload: Any) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)


def _slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", text.strip().lower())
    value = value.strip("_")
    if value:
        return value
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"theme_{digest}"
