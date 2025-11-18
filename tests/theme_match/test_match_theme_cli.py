"""match-theme CLI 测试，确保参数与输出正确。"""

import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from vidsynth.cli import app
from vidsynth.core import Clip, PipelineConfig, ThemeQuery, ThemeScore

runner = CliRunner()


def _write_clip_fixture(path: Path) -> None:
    clip = Clip(
        video_id="demo",
        clip_id=0,
        t_start=0.0,
        t_end=1.0,
        fps_keyframe=1.0,
        vis_emb_avg=(0.1, 0.2, 0.3),
        emb_model="openclip::ViT-B-32::laion400m_e32",
        created_at=datetime.now(tz=timezone.utc),
    )
    path.write_text(json.dumps([clip.to_dict()]), encoding="utf-8")


def test_match_theme_cli_writes_json(monkeypatch, tmp_path):
    clips_path = tmp_path / "clips.json"
    _write_clip_fixture(clips_path)
    output_path = tmp_path / "scores.json"

    class DummyMatcher:
        def __init__(self, *args, **kwargs):
            self.last_threshold = None

        def score_clips(self, clips, query):  # type: ignore[override]
            self.clips = clips
            self.query = query
            return [
                ThemeScore(
                    clip_id=clip.clip_id,
                    video_id=clip.video_id,
                    theme=query.theme,
                    score=0.9,
                    s_pos=0.95,
                    s_neg=0.05,
                    emb_model=clip.emb_model,
                    created_at=datetime.now(tz=timezone.utc),
                )
                for clip in clips
            ]

        def filter_scores(self, scores, threshold=None):  # type: ignore[override]
            self.last_threshold = threshold
            return scores

    dummy = DummyMatcher()
    monkeypatch.setattr("vidsynth.cli.ThemeMatcher", lambda *args, **kwargs: dummy)
    monkeypatch.setattr("vidsynth.cli.load_config", lambda *_, **__: PipelineConfig())
    monkeypatch.setattr("vidsynth.cli.build_theme_query", lambda *args, **kwargs: ThemeQuery.from_keywords("beach", ["beach"], []))

    result = runner.invoke(
        app,
        [
            "match-theme",
            str(clips_path),
            "beach",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload[0]["score"] == 0.9
    assert dummy.last_threshold == PipelineConfig().theme_match.score_threshold


def test_match_theme_cli_supports_csv(monkeypatch, tmp_path):
    clips_path = tmp_path / "clips.json"
    _write_clip_fixture(clips_path)
    output_path = tmp_path / "scores.csv"

    class DummyMatcher:
        def __init__(self, *args, **kwargs):
            pass

        def score_clips(self, clips, query):  # type: ignore[override]
            return [
                ThemeScore(
                    clip_id=0,
                    video_id="demo",
                    theme=query.theme,
                    score=0.4,
                    s_pos=0.5,
                    s_neg=0.1,
                    emb_model="openclip::ViT-B-32::laion400m_e32",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]

        def filter_scores(self, scores, threshold=None):  # type: ignore[override]
            return scores

    monkeypatch.setattr("vidsynth.cli.ThemeMatcher", lambda *args, **kwargs: DummyMatcher(*args, **kwargs))
    monkeypatch.setattr("vidsynth.cli.load_config", lambda *_, **__: PipelineConfig())
    monkeypatch.setattr("vidsynth.cli.build_theme_query", lambda *args, **kwargs: ThemeQuery.from_keywords("city", ["city"], []))

    result = runner.invoke(
        app,
        [
            "match-theme",
            str(clips_path),
            "city",
            "--output",
            str(output_path),
            "--format",
            "csv",
            "--score-threshold",
            "0.3",
        ],
    )

    assert result.exit_code == 0
    content = output_path.read_text(encoding="utf-8").splitlines()
    assert content[0].startswith("clip_id")
    assert "0.4" in content[1]
