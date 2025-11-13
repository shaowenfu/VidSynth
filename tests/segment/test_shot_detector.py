"""Shot detection 测试。"""

from pathlib import Path

import numpy as np

from vidsynth.core.config import SegmentConfig
from vidsynth.segment.shot_detector import detect_shots
from vidsynth.segment.types import EmbeddedSample, FrameSample


def make_sample(timestamp: float, color: int) -> EmbeddedSample:
    frame = np.full((4, 4, 3), color, dtype=np.uint8)
    embedding = np.array([color, 0, 0], dtype=np.float32)
    return EmbeddedSample(
        sample=FrameSample(
            video_path=Path("dummy.mp4"),
            frame_index=int(timestamp * 2),
            timestamp=timestamp,
            frame=frame,
        ),
        embedding=embedding,
    )


def test_detect_shots_single_segment() -> None:
    samples = [make_sample(0.0, 10), make_sample(1.0, 10), make_sample(2.0, 10)]
    cfg = SegmentConfig()

    boundaries = detect_shots(samples, cfg)

    assert boundaries == [(0, 3)]


def test_detect_shots_split_on_color_change() -> None:
    samples = [
        make_sample(0.0, 10),
        make_sample(1.0, 10),
        make_sample(2.0, 200),
        make_sample(3.0, 200),
    ]
    cfg = SegmentConfig(cosine_threshold=0.1, histogram_threshold=0.1)

    boundaries = detect_shots(samples, cfg)

    assert boundaries == [(0, 2), (2, 4)]
