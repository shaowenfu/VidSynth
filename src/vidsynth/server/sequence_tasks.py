"""Sequencing task queue and SSE logging."""

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
from typing import Any, Deque, Dict, Iterable, List, Optional

from vidsynth.core import Clip, ThemeScore, get_logger, load_config
from vidsynth.core.logging_utils import attach_sse_handler
from vidsynth.sequence import Sequencer

from .events import EventBroadcaster
from .workspace import EDL_DIR, SEGMENTATION_DIR, THEMES_DIR, ensure_workspace_layout


@dataclass(slots=True)
class SequenceJob:
    theme: str
    theme_slug: str
    video_ids: List[str]
    force: bool
    threshold_upper: float
    threshold_lower: float
    min_seconds: Optional[float]
    max_seconds: Optional[float]
    merge_gap: Optional[float]


@dataclass(slots=True)
class SequenceStatus:
    theme: str
    theme_slug: str
    status: str
    progress: float
    message: str
    updated_at: str
    video_id: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme": self.theme,
            "theme_slug": self.theme_slug,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "updated_at": self.updated_at,
            "video_id": self.video_id,
        }


class SequenceTaskManager:
    """Single-worker queue for sequencing tasks."""

    def __init__(self, broadcaster: EventBroadcaster) -> None:
        self._lock = threading.Lock()
        self._queue: Deque[SequenceJob] = deque()
        self._active: Optional[SequenceJob] = None
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
        video_ids: Iterable[str],
        force: bool,
        threshold_upper: float,
        threshold_lower: float,
        min_seconds: Optional[float],
        max_seconds: Optional[float],
        merge_gap: Optional[float],
    ) -> Dict[str, Any]:
        ensure_workspace_layout()
        resolved_slug = theme_slug or _slugify(theme)
        targets = [video_id for video_id in video_ids if video_id]
        if not targets:
            targets = self._default_video_ids(resolved_slug)
        if not targets:
            return {"theme": theme, "theme_slug": resolved_slug, "status": "skipped"}

        cached: List[str] = []
        pending: List[str] = []
        for video_id in targets:
            if not force and self._edl_path(resolved_slug, video_id).exists():
                cached.append(video_id)
            else:
                pending.append(video_id)

        if cached:
            self._write_status(
                theme=theme,
                theme_slug=resolved_slug,
                status="cached",
                progress=1.0 if not pending else 0.0,
                message="cached",
                video_id=None,
            )
            self._publish_status(resolved_slug)

        if not pending:
            return {
                "theme": theme,
                "theme_slug": resolved_slug,
                "status": "cached",
                "cached": cached,
                "result_path": f"edl/{resolved_slug}/{cached[0]}/edl.json" if cached else None,
            }

        with self._lock:
            if self._active and self._active.theme_slug == resolved_slug:
                return {"theme": theme, "theme_slug": resolved_slug, "status": "skipped"}
            self._queue.append(
                SequenceJob(
                    theme=theme,
                    theme_slug=resolved_slug,
                    video_ids=pending,
                    force=force,
                    threshold_upper=threshold_upper,
                    threshold_lower=threshold_lower,
                    min_seconds=min_seconds,
                    max_seconds=max_seconds,
                    merge_gap=merge_gap,
                )
            )
            self._write_status(
                theme=theme,
                theme_slug=resolved_slug,
                status="queued",
                progress=0.0,
                message="queued",
                video_id=None,
            )
        self._publish_status(resolved_slug)
        return {
            "theme": theme,
            "theme_slug": resolved_slug,
            "status": "queued",
            "queued": pending,
            "cached": cached,
        }

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

    def _run_job(self, job: SequenceJob) -> None:
        current_video: str | None = None
        current_progress = 0.0
        logger = get_logger("vidsynth.sequence")
        logger.setLevel("INFO")

        def emit_log(message: str, _record: Any) -> None:
            event = {
                "stage": "sequence",
                "theme": job.theme,
                "video_id": current_video,
                "status": "running",
                "progress": current_progress,
                "message": message,
                "result_path": None,
            }
            self._broadcaster.publish(event)

        handler = attach_sse_handler(logger, emit_log)
        try:
            scores_payload = self._read_scores(job.theme_slug)
            meta = scores_payload.get("meta", {})
            theme_value = job.theme or meta.get("theme") or job.theme_slug
            emb_model = meta.get("emb_model") or ""
            score_map = scores_payload.get("scores", {})
            total = len(job.video_ids)
            for index, video_id in enumerate(job.video_ids):
                current_video = video_id
                clips = self._load_clips(video_id)
                entries = score_map.get(video_id) or []
                if not clips or not entries:
                    logger.info("FILTER skip video_id=%s reason=missing_data", video_id)
                    continue
                scores = self._to_scores(entries, video_id, theme_value, emb_model)
                sequencer = Sequencer(
                    threshold_upper=job.threshold_upper,
                    threshold_lower=job.threshold_lower,
                    min_clip_seconds=job.min_seconds,
                    max_clip_seconds=job.max_seconds,
                    merge_gap=job.merge_gap,
                )
                result = sequencer.sequence(clips, scores)
                self._write_edl(job.theme_slug, video_id, result.edl)
                current_progress = (index + 1) / total if total else 1.0
                self._write_status(
                    theme=theme_value,
                    theme_slug=job.theme_slug,
                    status="running",
                    progress=current_progress,
                    message=f"sequenced {video_id}",
                    video_id=video_id,
                )
                self._publish_status(job.theme_slug)
                done_event = {
                    "stage": "sequence",
                    "theme": theme_value,
                    "video_id": video_id,
                    "status": "done",
                    "progress": current_progress,
                    "message": "done",
                    "result_path": f"edl/{job.theme_slug}/{video_id}/edl.json",
                }
                self._broadcaster.publish(done_event)
            self._write_status(
                theme=theme_value,
                theme_slug=job.theme_slug,
                status="done",
                progress=1.0,
                message="done",
                video_id=None,
            )
            self._publish_status(job.theme_slug)
        except Exception as exc:
            self._write_status(
                theme=job.theme,
                theme_slug=job.theme_slug,
                status="error",
                progress=0.0,
                message=str(exc),
                video_id=current_video,
            )
            self._publish_status(job.theme_slug)
        finally:
            logger.removeHandler(handler)

    def _default_video_ids(self, theme_slug: str) -> List[str]:
        scores = self._read_scores(theme_slug)
        score_map = scores.get("scores", {})
        return sorted([video_id for video_id in score_map.keys() if video_id])

    def _read_scores(self, theme_slug: str) -> Dict[str, Any]:
        path = THEMES_DIR / theme_slug / "scores.json"
        if not path.exists():
            raise FileNotFoundError(f"scores.json not found for theme {theme_slug}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("invalid scores payload") from exc

    def _load_clips(self, video_id: str) -> List[Clip]:
        path = SEGMENTATION_DIR / video_id / "clips.json"
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        clips: List[Clip] = []
        for item in payload:
            if isinstance(item, dict):
                try:
                    clips.append(Clip.from_dict(item))
                except Exception:
                    continue
        return clips

    def _to_scores(
        self,
        entries: List[Dict[str, Any]],
        video_id: str,
        theme: str,
        emb_model: str,
    ) -> List[ThemeScore]:
        now = datetime.now(tz=timezone.utc)
        scores: List[ThemeScore] = []
        for entry in entries:
            scores.append(
                ThemeScore(
                    clip_id=int(entry.get("clip_id", 0)),
                    video_id=video_id,
                    theme=theme,
                    score=float(entry.get("score", 0.0)),
                    s_pos=float(entry.get("s_pos", 0.0)),
                    s_neg=float(entry.get("s_neg", 0.0)),
                    emb_model=emb_model,
                    created_at=now,
                    metadata={"source": "scores.json"},
                )
            )
        return scores

    def _edl_path(self, theme_slug: str, video_id: str) -> Path:
        return EDL_DIR / theme_slug / video_id / "edl.json"

    def _write_edl(self, theme_slug: str, video_id: str, items: Iterable[Any]) -> None:
        path = self._edl_path(theme_slug, video_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {"video_id": item.video_id, "t_start": item.t_start, "t_end": item.t_end, "reason": item.reason}
            for item in items
        ]
        self._atomic_write_json(path, payload)

    def _status_path(self, theme_slug: str) -> Path:
        return EDL_DIR / theme_slug / "status.json"

    def _write_status(
        self,
        *,
        theme: str,
        theme_slug: str,
        status: str,
        progress: float,
        message: str,
        video_id: str | None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        normalized = max(0.0, min(1.0, float(progress)))
        payload = SequenceStatus(
            theme=theme,
            theme_slug=theme_slug,
            status=status,
            progress=normalized,
            message=message,
            updated_at=now,
            video_id=video_id,
        ).to_dict()
        path = self._status_path(theme_slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_json(path, payload)

    def _read_status(self, theme_slug: str) -> Optional[Dict[str, Any]]:
        path = self._status_path(theme_slug)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _publish_status(self, theme_slug: str) -> None:
        status = self._read_status(theme_slug)
        if not status:
            return
        self._broadcaster.publish(self._status_to_event(status))

    @staticmethod
    def _status_to_event(payload: Dict[str, Any]) -> Dict[str, Any]:
        theme = payload.get("theme")
        theme_slug = payload.get("theme_slug")
        status = payload.get("status")
        result_path = None
        if status in {"done", "cached"} and theme_slug and payload.get("video_id"):
            result_path = f"edl/{theme_slug}/{payload['video_id']}/edl.json"
        return {
            "stage": "sequence",
            "theme": theme,
            "video_id": payload.get("video_id"),
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
