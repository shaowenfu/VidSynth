"""Theme matching task queue and persistence."""

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
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional

import cv2

from vidsynth.core import Clip, ThemeQuery
from vidsynth.theme_match import ThemeMatcher

from .events import EventBroadcaster
from .workspace import SEGMENTATION_DIR, THEMES_DIR, VIDEOS_DIR, ensure_workspace_layout


@dataclass(slots=True)
class ThemeJob:
    theme: str
    theme_slug: str
    positives: List[str]
    negatives: List[str]
    video_ids: List[str]
    force: bool


@dataclass(slots=True)
class ThemeTaskStatus:
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


class ThemeTaskManager:
    """Single-worker queue for theme matching tasks."""

    def __init__(
        self,
        broadcaster: EventBroadcaster,
        matcher_factory: Callable[[], ThemeMatcher],
    ) -> None:
        self._lock = threading.Lock()
        self._queue: Deque[ThemeJob] = deque()
        self._active: Optional[ThemeJob] = None
        self._broadcaster = broadcaster
        self._matcher_factory = matcher_factory
        ensure_workspace_layout()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def enqueue(
        self,
        *,
        theme: str,
        positives: Iterable[str],
        negatives: Iterable[str],
        video_ids: Iterable[str],
        force: bool,
    ) -> Dict[str, Any]:
        ensure_workspace_layout()
        theme_slug = _slugify(theme)
        clean_pos = _clean_list(positives)
        clean_neg = _clean_list(negatives)
        if not clean_pos and not clean_neg:
            clean_pos = [theme]
        scores_path = self._scores_path(theme_slug)
        if scores_path.exists() and not force:
            self._write_status(
                theme=theme,
                theme_slug=theme_slug,
                status="cached",
                progress=1.0,
                message="cached",
                video_id=None,
            )
            self._publish_status(theme_slug)
            return {
                "theme": theme,
                "theme_slug": theme_slug,
                "status": "cached",
                "result_path": f"themes/{theme_slug}/scores.json",
            }
        with self._lock:
            if self._active and self._active.theme_slug == theme_slug:
                return {"theme": theme, "theme_slug": theme_slug, "status": "skipped"}
            if any(job.theme_slug == theme_slug for job in self._queue):
                return {"theme": theme, "theme_slug": theme_slug, "status": "skipped"}
            job = ThemeJob(
                theme=theme,
                theme_slug=theme_slug,
                positives=clean_pos,
                negatives=clean_neg,
                video_ids=list(video_ids),
                force=force,
            )
            self._queue.append(job)
            self._write_status(
                theme=theme,
                theme_slug=theme_slug,
                status="queued",
                progress=0.0,
                message="queued",
                video_id=None,
            )
        self._publish_status(theme_slug)
        return {"theme": theme, "theme_slug": theme_slug, "status": "queued"}

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

    def _run_job(self, job: ThemeJob) -> None:
        try:
            self._write_status(
                theme=job.theme,
                theme_slug=job.theme_slug,
                status="running",
                progress=0.0,
                message="starting",
                video_id=None,
            )
            self._publish_status(job.theme_slug)
            video_ids = self._resolve_video_ids(job.video_ids)
            if not video_ids:
                raise ValueError("no segmentation results available")
            clips_by_video: Dict[str, List[Clip]] = {}
            total_clips = 0
            for video_id in video_ids:
                clips = self._load_clips(video_id)
                if clips:
                    clips_by_video[video_id] = clips
                    total_clips += len(clips)
            if total_clips == 0:
                raise ValueError("no clips loaded")
            matcher = self._matcher_factory()
            query = ThemeQuery.from_keywords(theme=job.theme, positives=job.positives, negatives=job.negatives)
            scores_payload: Dict[str, Any] = {"meta": {}, "scores": {}}
            processed = 0
            emb_model = None
            for video_id in video_ids:
                clips = clips_by_video.get(video_id, [])
                if not clips:
                    continue
                emb_model = emb_model or clips[0].emb_model
                scores = matcher.score_clips(clips, query)
                clip_lookup = {clip.clip_id: clip for clip in clips}
                entries = []
                for score in scores:
                    clip = clip_lookup.get(score.clip_id)
                    if not clip:
                        continue
                    entries.append(
                        {
                            "clip_id": score.clip_id,
                            "score": score.score,
                            "s_pos": score.s_pos,
                            "s_neg": score.s_neg,
                            "t_start": clip.t_start,
                            "t_end": clip.t_end,
                        }
                    )
                entries.sort(key=lambda item: item["t_start"])
                self._attach_thumbnails(video_id, entries, force=job.force)
                scores_payload["scores"][video_id] = entries
                processed += len(clips)
                progress = processed / total_clips if total_clips else 0.0
                self._write_status(
                    theme=job.theme,
                    theme_slug=job.theme_slug,
                    status="running",
                    progress=progress,
                    message=f"scoring {video_id}",
                    video_id=video_id,
                )
                self._publish_status(job.theme_slug)
            scores_payload["meta"] = {
                "theme": job.theme,
                "theme_slug": job.theme_slug,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "positives": list(job.positives),
                "negatives": list(job.negatives),
                "emb_model": emb_model,
            }
            self._write_scores(job.theme_slug, scores_payload)
            self._write_status(
                theme=job.theme,
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
                video_id=None,
            )
            self._publish_status(job.theme_slug)

    def _resolve_video_ids(self, video_ids: Iterable[str]) -> List[str]:
        resolved = [video_id for video_id in video_ids if video_id]
        if resolved:
            return resolved
        if not SEGMENTATION_DIR.exists():
            return []
        return sorted(
            [
                path.name
                for path in SEGMENTATION_DIR.iterdir()
                if path.is_dir() and (path / "clips.json").exists()
            ]
        )

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

    def _resolve_video_path(self, video_id: str) -> Optional[Path]:
        if not VIDEOS_DIR.exists():
            return None
        for path in VIDEOS_DIR.iterdir():
            if path.is_file() and path.stem == video_id:
                return path
        return None

    def _attach_thumbnails(self, video_id: str, entries: List[Dict[str, Any]], *, force: bool = False) -> None:
        if not entries:
            return
        video_path = self._resolve_video_path(video_id)
        if not video_path:
            return
        thumbs_dir = SEGMENTATION_DIR / video_id / "thumbs"
        thumbs_dir.mkdir(parents=True, exist_ok=True)
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return
        try:
            for entry in entries:
                clip_id = entry.get("clip_id")
                if clip_id is None:
                    continue
                thumb_path = thumbs_dir / f"{clip_id}.jpg"
                thumb_rel = f"segmentation/{video_id}/thumbs/{clip_id}.jpg"
                if thumb_path.exists():
                    if not force:
                        entry["thumb_url"] = thumb_rel
                        continue
                    thumb_path.unlink()
                t_start = float(entry.get("t_start", 0.0))
                capture.set(cv2.CAP_PROP_POS_MSEC, max(t_start, 0.0) * 1000.0)
                success, frame = capture.read()
                if not success:
                    continue
                if cv2.imwrite(str(thumb_path), frame):
                    entry["thumb_url"] = thumb_rel
        finally:
            capture.release()

    def _status_path(self, theme_slug: str) -> Path:
        return THEMES_DIR / theme_slug / "status.json"

    def _scores_path(self, theme_slug: str) -> Path:
        return THEMES_DIR / theme_slug / "scores.json"

    def _write_scores(self, theme_slug: str, payload: Dict[str, Any]) -> None:
        path = self._scores_path(theme_slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_json(path, payload)

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
        payload = ThemeTaskStatus(
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
        if status in {"done", "cached"} and theme_slug:
            result_path = f"themes/{theme_slug}/scores.json"
        return {
            "stage": "theme_match",
            "theme": theme,
            "video_id": payload.get("video_id"),
            "status": status,
            "progress": payload.get("progress"),
            "message": payload.get("message"),
            "result_path": result_path,
        }

    @staticmethod
    def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)


def _clean_list(values: Iterable[str]) -> List[str]:
    seen = set()
    cleaned: List[str] = []
    for item in values:
        text = str(item).strip()
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return cleaned


def _slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", text.strip().lower())
    value = value.strip("_")
    if value:
        return value
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"theme_{digest}"
