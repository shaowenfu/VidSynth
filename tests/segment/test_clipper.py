"""Clip builder 测试。"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from vidsynth.core.config import SegmentConfig
from vidsynth.segment.clipper import build_clips_from_samples
from vidsynth.segment.types import EmbeddedSample, FrameSample


def make_samples() -> list[EmbeddedSample]:
    base_time = 0.0
    samples = []
    for idx in range(4):
        timestamp = base_time + idx
        frame = np.zeros((2, 2, 3), dtype=np.uint8)
        embedding = np.array([idx + 1, 0, 0], dtype=np.float32)
        samples.append(
            EmbeddedSample(
                sample=FrameSample(
                    video_path=Path("dummy.mp4"),
                    frame_index=idx,
                    timestamp=timestamp,
                    frame=frame,
                ),
                embedding=embedding,
            )
        )
    return samples


def test_build_clips_basic() -> None:
    samples = make_samples()
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
    assert clip.vis_emb_avg[0] == 2.5
