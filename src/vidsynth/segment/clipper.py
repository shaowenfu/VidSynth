"""封装从关键帧到 Clip 列表的流程。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

import numpy as np

from vidsynth.core import Clip, PipelineConfig
from vidsynth.core.config import SegmentConfig

from .embedding import DEFAULT_EMBEDDER, EmbeddingBackend
from .loader import FrameSample, iter_keyframes
from .shot_detector import detect_shots
from .types import EmbeddedSample


@dataclass(slots=True)
class SegmentResult:
    """封装单个视频的切分结果，便于后续统计。"""

    video_id: str
    clips: List[Clip]
    discarded_segments: int


def segment_video(
    video_id: str,
    video_path: str | Path,
    config: PipelineConfig,
    *,
    embedder: EmbeddingBackend | None = None,
) -> SegmentResult:
    """主入口：读取视频 -> 采样 -> embedding -> 镜头切分 -> Clip 列表。"""

    seg_cfg = config.segment
    embedder = embedder or DEFAULT_EMBEDDER

    samples: List[EmbeddedSample] = []
    for sample in iter_keyframes(video_path, seg_cfg.fps_keyframe):
        embedding = embedder.embed_frame(sample.frame)
        samples.append(EmbeddedSample(sample=sample, embedding=embedding))

    if not samples:
        return SegmentResult(video_id=video_id, clips=[], discarded_segments=0)

    boundaries = detect_shots(samples, seg_cfg)
    clips = build_clips_from_samples(
        video_id=video_id,
        samples=samples,
        boundaries=boundaries,
        seg_cfg=seg_cfg,
        emb_model_name=embedder.emb_model_name,
    )
    discarded = len(boundaries) - len(clips)
    return SegmentResult(video_id=video_id, clips=clips, discarded_segments=discarded)


def build_clips_from_samples(
    *,
    video_id: str,
    samples: Sequence[EmbeddedSample],
    boundaries: Sequence[tuple[int, int]] | None = None,
    seg_cfg: SegmentConfig,
    emb_model_name: str,
) -> List[Clip]:
    """根据指定边界生成 Clip 列表，方便单元测试复用。"""

    if not samples:
        return []
    regions = boundaries if boundaries is not None else [(0, len(samples))]
    clips: List[Clip] = []
    clip_id = 0
    for start_idx, end_idx in regions:
        subset = samples[start_idx:end_idx]
        if not subset:
            continue
        duration = _duration(subset)
        if duration < seg_cfg.min_clip_seconds:
            # TODO: 未来在此合并邻接片段，而不是直接丢弃
            continue
        if duration > seg_cfg.max_clip_seconds:
            end_time = subset[0].timestamp + seg_cfg.max_clip_seconds
        else:
            end_time = subset[-1].timestamp
        avg_embedding = np.mean([sample.embedding for sample in subset], axis=0)
        clip = Clip(
            video_id=video_id,
            clip_id=clip_id,
            t_start=subset[0].timestamp,
            t_end=end_time,
            fps_keyframe=seg_cfg.fps_keyframe,
            vis_emb_avg=tuple(float(x) for x in avg_embedding.tolist()),
            emb_model=emb_model_name,
            created_at=datetime.now(timezone.utc),
        )
        clips.append(clip)
        clip_id += 1
    return clips


def _duration(subset: Sequence[EmbeddedSample]) -> float:
    if len(subset) == 1:
        return 0.0
    return max(0.0, subset[-1].timestamp - subset[0].timestamp)
