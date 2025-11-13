"""Clip builder 测试，覆盖合并/拆分逻辑。"""

from pathlib import Path

import numpy as np

from vidsynth.core.config import SegmentConfig
from vidsynth.segment.clipper import build_clips_from_samples
from vidsynth.segment.types import EmbeddedSample, FrameSample


def _sample(timestamp: float, value: float) -> EmbeddedSample:
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    embedding = np.array([value, 0, 0], dtype=np.float32)
    return EmbeddedSample(
        sample=FrameSample(
            video_path=Path("dummy.mp4"),
            frame_index=int(timestamp * 2),
            timestamp=timestamp,
            frame=frame,
        ),
        embedding=embedding,
    )


def test_build_clips_basic() -> None:
    samples = [_sample(ts, ts + 1) for ts in (0.0, 1.0, 2.0, 3.0)]
    cfg = SegmentConfig(min_clip_seconds=1.5, max_clip_seconds=6.0)

    clips = build_clips_from_samples(
        video_id="vid-1",
        samples=samples,
        boundaries=[(0, len(samples))],
        seg_cfg=cfg,
        emb_model_name="test-model",
    )

    assert len(clips) == 1
    clip = clips[0]
    assert clip.t_start == 0.0
    assert clip.t_end == 3.0
    assert clip.emb_model == "test-model"


def test_merge_short_segments() -> None:
    # 每段持续 0.5s，小于 min_clip_seconds，期望自动合并
    samples = [_sample(idx * 0.5, idx) for idx in range(6)]
    cfg = SegmentConfig(min_clip_seconds=1.0, max_clip_seconds=6.0, merge_short_segments=True)
    boundaries = [(0, 2), (2, 4), (4, 6)]

    clips = build_clips_from_samples(
        video_id="vid-2",
        samples=samples,
        boundaries=boundaries,
        seg_cfg=cfg,
        emb_model_name="test-model",
    )

    assert len(clips) == 2  # 前两段合并，最后一段保持
    assert clips[0].t_start == 0.0
    assert clips[0].t_end >= 1.0


def test_split_long_segments() -> None:
    samples = [_sample(float(idx), idx) for idx in range(10)]  # 0-9s
    cfg = SegmentConfig(max_clip_seconds=3.0, split_long_segments=True)

    clips = build_clips_from_samples(
        video_id="vid-3",
        samples=samples,
        boundaries=[(0, len(samples))],
        seg_cfg=cfg,
        emb_model_name="test-model",
    )

    assert len(clips) >= 3
    assert all((clip.t_end - clip.t_start) <= cfg.max_clip_seconds for clip in clips)
