"""CLI 行为测试。"""

import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from vidsynth.cli import app
from vidsynth.core import Clip, PipelineConfig

runner = CliRunner()


def test_segment_video_cli(monkeypatch, tmp_path):
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"fake")
    output = tmp_path / "out" / "clips.json"

    clip = Clip(
        video_id="demo",
        clip_id=0,
        t_start=0.0,
        t_end=1.0,
        fps_keyframe=1.0,
        vis_emb_avg=(0.1, 0.2, 0.3),
        emb_model="stub",
        created_at=datetime.now(timezone.utc),
    )

    class DummyResult:
        def __init__(self):
            self.clips = [clip]
            self.discarded_segments = 0

    monkeypatch.setattr("vidsynth.cli.load_config", lambda *_, **__: PipelineConfig())
    monkeypatch.setattr("vidsynth.cli.segment_video", lambda **kwargs: DummyResult())

    result = runner.invoke(
        app,
        [
            "segment-video",
            str(video),
            "--output",
            str(output),
            "--embedding-backend",
            "mean_color",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output.read_text())
    assert len(data) == 1
    assert data[0]["video_id"] == "demo"
