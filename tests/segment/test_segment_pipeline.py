"""端到端最小流水测试，使用 stub embedder + fake loader。"""

from pathlib import Path

import numpy as np

from vidsynth.core import PipelineConfig
from vidsynth.segment.clipper import segment_video
from vidsynth.segment.types import FrameSample


class StubEmbedder:
    emb_model_name = "stub"

    def embed_frame(self, frame):  # type: ignore[override]
        value = float(frame[0, 0, 0])
        return np.array([value, 0, 0], dtype=np.float32)


def fake_iter_keyframes(_video_path, _fps):
    frames = []
    for idx in range(6):
        color = 10 if idx < 3 else 200
        frame = np.full((2, 2, 3), color, dtype=np.uint8)
        frames.append(
            FrameSample(
                video_path=Path("dummy.mp4"),
                frame_index=idx,
                timestamp=float(idx),
                frame=frame,
            )
        )
    for sample in frames:
        yield sample


def test_segment_video_pipeline(monkeypatch):
    monkeypatch.setattr("vidsynth.segment.clipper.iter_keyframes", fake_iter_keyframes)

    cfg = PipelineConfig()
    result = segment_video(
        video_id="vid-A",
        video_path="dummy.mp4",
        config=cfg,
        embedder=StubEmbedder(),
    )

    assert len(result.clips) == 2
    assert result.discarded_segments == 0
    assert result.clips[0].clip_id == 0
    assert result.clips[1].clip_id == 1
