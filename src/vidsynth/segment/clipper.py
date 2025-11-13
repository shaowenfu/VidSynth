"""封装从关键帧到 Clip 列表的流程。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

import numpy as np

from vidsynth.core import Clip, PipelineConfig
from vidsynth.core.config import SegmentConfig

from .embedding import DEFAULT_EMBEDDER, EmbeddingBackend, create_embedder
from .loader import iter_keyframes
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
    embedder = embedder or create_embedder(config.embedding)

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
    discarded = max(0, len(boundaries) - len(clips))
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
    regions = list(boundaries if boundaries is not None else [(0, len(samples))])
    regions = _merge_short_regions(samples, regions, seg_cfg)

    clips: List[Clip] = []
    clip_id = 0
    for start_idx, end_idx in regions:
        subset = samples[start_idx:end_idx]
        if not subset:
            continue
        for chunk in _split_subset(subset, seg_cfg):
            if not chunk:
                continue
            duration = _duration(chunk)
            if duration < seg_cfg.min_clip_seconds and not seg_cfg.keep_last_short_segment:
                continue
            clip = _create_clip(
                video_id=video_id,
                clip_id=clip_id,
                samples=chunk,
                seg_cfg=seg_cfg,
                emb_model_name=emb_model_name,
            )
            clips.append(clip)
            clip_id += 1
    return clips


def _duration(subset: Sequence[EmbeddedSample]) -> float:
    if len(subset) == 1:
        return 0.0
    return max(0.0, subset[-1].timestamp - subset[0].timestamp)


def _merge_short_regions(
    samples: Sequence[EmbeddedSample],
    regions: Sequence[tuple[int, int]],
    seg_cfg: SegmentConfig,
) -> List[tuple[int, int]]:
    if not seg_cfg.merge_short_segments:
        return list(regions)
    merged: List[tuple[int, int]] = []
    i = 0
    total = len(regions)
    while i < total:
        start = regions[i][0]
        end = regions[i][1]
        duration = _duration(samples[start:end])
        while duration < seg_cfg.min_clip_seconds and i + 1 < total:
            i += 1
            end = regions[i][1]
            duration = _duration(samples[start:end])
        merged.append((start, end))
        i += 1
    return merged


def _split_subset(
    subset: Sequence[EmbeddedSample],
    seg_cfg: SegmentConfig,
) -> List[Sequence[EmbeddedSample]]:
    if not seg_cfg.split_long_segments:
        return [subset]
    duration = _duration(subset)
    if duration <= seg_cfg.max_clip_seconds:
        return [subset]
    chunks: List[Sequence[EmbeddedSample]] = []
    chunk: List[EmbeddedSample] = []
    chunk_start = subset[0].timestamp
    for sample in subset:
        if not chunk:
            chunk.append(sample)
            chunk_start = sample.timestamp
            continue
        if sample.timestamp - chunk_start <= seg_cfg.max_clip_seconds:
            chunk.append(sample)
        else:
            chunks.append(chunk)
            chunk = [sample]
            chunk_start = sample.timestamp
    if chunk:
        chunks.append(chunk)
    return chunks


def _create_clip(
    *,
    video_id: str,
    clip_id: int,
    samples: Sequence[EmbeddedSample],
    seg_cfg: SegmentConfig,
    emb_model_name: str,
) -> Clip:
    avg_embedding = np.mean([sample.embedding for sample in samples], axis=0)
    t_start = samples[0].timestamp
    max_end = t_start + seg_cfg.max_clip_seconds
    actual_end = samples[-1].timestamp
    t_end = min(actual_end, max_end) if seg_cfg.split_long_segments else actual_end
    return Clip(
        video_id=video_id,
        clip_id=clip_id,
        t_start=t_start,
        t_end=t_end,
        fps_keyframe=seg_cfg.fps_keyframe,
        vis_emb_avg=tuple(float(x) for x in avg_embedding.tolist()),
        emb_model=emb_model_name,
        created_at=datetime.now(timezone.utc),
    )
