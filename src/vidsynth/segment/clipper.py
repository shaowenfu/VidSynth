"""封装从关键帧到 Clip 列表的流程。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Sequence

import numpy as np

from vidsynth.core import Clip, PipelineConfig
from vidsynth.core.config import SegmentConfig

from .embedding import DEFAULT_EMBEDDER, EmbeddingBackend, create_embedder
from .loader import estimate_keyframe_count, iter_keyframes
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
    progress_callback: Callable[[float], None] | None = None,
) -> SegmentResult:
    """主入口：读取视频 -> 采样 -> embedding -> 镜头切分 -> Clip 列表。"""

    seg_cfg = config.segment
    embedder = embedder or create_embedder(config.embedding)

    samples: List[EmbeddedSample] = []
    total_samples = 0
    step = 0
    if progress_callback is not None:
        try:
            total_samples, _ = estimate_keyframe_count(video_path, seg_cfg.fps_keyframe)
        except Exception:
            total_samples = 0
        step = max(total_samples // 100, 1) if total_samples else 0

    processed = 0
    for sample in iter_keyframes(video_path, seg_cfg.fps_keyframe):
        embedding = embedder.embed_frame(sample.frame)
        samples.append(EmbeddedSample(sample=sample, embedding=embedding))
        if progress_callback is not None and total_samples > 0:
            processed += 1
            if processed % step == 0 or processed == total_samples:
                progress_callback(min(processed / total_samples, 1.0))

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
    if progress_callback is not None:
        progress_callback(1.0)
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
    """将过长的视频片段拆分成多个小片段，确保每个片段不超过最大时长限制。"""
    
    # 如果禁用长片段拆分，直接返回原片段
    if not seg_cfg.split_long_segments:
        return [subset]
    
    # 计算当前片段总时长
    duration = _duration(subset)
    
    # 如果总时长未超过限制，无需拆分
    if duration <= seg_cfg.max_clip_seconds:
        return [subset]
    
    # 初始化拆分结果列表和当前块
    chunks: List[Sequence[EmbeddedSample]] = []
    chunk: List[EmbeddedSample] = []
    chunk_start = subset[0].timestamp
    
    # 遍历所有样本，按时间戳拆分
    for sample in subset:
        # 如果当前块为空，添加第一个样本并记录起始时间
        if not chunk:
            chunk.append(sample)
            chunk_start = sample.timestamp
            continue
            
        # 如果当前样本仍在时间限制内，添加到当前块
        if sample.timestamp - chunk_start <= seg_cfg.max_clip_seconds:
            chunk.append(sample)
        else:
            # 否则完成当前块，开始新块
            chunks.append(chunk)
            chunk = [sample]
            chunk_start = sample.timestamp
    
    # 添加最后一个块（如果存在）
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
    actual_end = samples[-1].timestamp

    if seg_cfg.split_long_segments:
        max_end = t_start + seg_cfg.max_clip_seconds
        t_end = min(actual_end, max_end)
    else:
        t_end = actual_end

    # 单帧区域会导致 t_end == t_start，回退到抽帧间隔，避免零长度 clip
    if t_end <= t_start:
        frame_interval = 1.0 / seg_cfg.fps_keyframe if seg_cfg.fps_keyframe > 0 else 1.0
        fallback_end = t_start + frame_interval
        if seg_cfg.split_long_segments:
            fallback_end = min(fallback_end, t_start + seg_cfg.max_clip_seconds)
        t_end = fallback_end

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
