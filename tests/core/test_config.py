"""配置加载器测试，覆盖默认及环境变量覆盖场景。"""

from pathlib import Path

import pytest

from vidsynth.core import PipelineConfig, load_config


def test_load_config_defaults() -> None:
    cfg = load_config()

    assert isinstance(cfg, PipelineConfig)
    assert cfg.segment.fps_keyframe == 1.0
    assert cfg.theme_match.score_threshold == 0.2
    assert cfg.assets_root.name == "assets"


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

    cfg = load_config(custom_cfg)

    assert cfg.segment.fps_keyframe == 2.5  # 环境变量覆盖文件值
    assert cfg.assets_root == (tmp_path / "assets-store").resolve()
