"""配置加载器测试，覆盖默认及环境变量覆盖场景。"""

from pathlib import Path

import pytest

from vidsynth.core import PipelineConfig, load_config


def test_load_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIDSYNTH_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("VIDSYNTH_WORKSPACE_ROOT", raising=False)
    cfg = load_config()
    repo_root = Path(__file__).resolve().parents[2]

    assert isinstance(cfg, PipelineConfig)
    assert cfg.segment.fps_keyframe == 1.0
    assert cfg.theme_match.score_threshold == 0.2
    assert cfg.embedding.backend == "mean_color"
    assert cfg.embedding.preset == "cpu-small"
    assert cfg.assets_root == (repo_root / "workspace" / "videos").resolve()


def test_load_config_with_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    custom_cfg = tmp_path / "custom.yaml"
    custom_cfg.write_text(
        """
segment:
  fps_keyframe: 0.5
        """.strip()
    )

    monkeypatch.setenv("VIDSYNTH_SEGMENT_FPS", "2.5")
    monkeypatch.setenv("VIDSYNTH_STORAGE_ROOT", str(tmp_path / "assets-store"))
    monkeypatch.setenv("VIDSYNTH_EMBEDDING_DEVICE", "cuda")

    cfg = load_config(custom_cfg)

    assert cfg.segment.fps_keyframe == 2.5  # 环境变量覆盖文件值
    assert cfg.assets_root == (tmp_path / "assets-store").resolve()
    assert cfg.embedding.device == "cuda"
