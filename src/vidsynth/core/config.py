"""配置加载工具，集中管理仓内/环境参数。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, MutableMapping, Sequence, Tuple

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .paths import ASSETS_ENV_KEY, resolve_assets_root

CONFIG_ENV_KEY = "VIDSYNTH_CONFIG_PATH"


class SegmentConfig(BaseModel):
    """片段切分相关参数，默认值与 MVP 文档保持一致。"""

    fps_keyframe: float = 1.0
    cosine_threshold: float = 0.3
    histogram_threshold: float = 0.45
    min_clip_seconds: float = 2.0
    max_clip_seconds: float = 6.0


class ThemeMatchConfig(BaseModel):
    """主题匹配阶段参数，后续可扩展多尺度得分策略。"""

    score_threshold: float = 0.2
    negative_weight: float = 0.8


class ExportConfig(BaseModel):
    """导出阶段参数，留好接口给后续码率/编码器切换。"""

    video_codec: str = "libx264"
    video_bitrate: str = "8M"
    audio_fade_ms: int = 150
    video_crossfade_ms: int = 200


class PipelineConfig(BaseModel):
    """聚合各阶段配置，并包含共享路径。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    segment: SegmentConfig = Field(default_factory=SegmentConfig)
    theme_match: ThemeMatchConfig = Field(default_factory=ThemeMatchConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    assets_root: Path = Field(default_factory=resolve_assets_root)
    raw: Dict[str, Any] = Field(default_factory=dict, description="原始配置字典，便于调试。")

    def model_post_init(self, __context: Any) -> None:  # type: ignore[override]
        # 保留原始配置便于后续 diff/日志输出
        if not self.raw:
            self.raw = self.to_raw_dict()

    def to_raw_dict(self) -> Dict[str, Any]:
        """导出基础 dict，供日志或远程存储使用。"""

        return {
            "segment": self.segment.model_dump(),
            "theme_match": self.theme_match.model_dump(),
            "export": self.export.model_dump(),
            "assets_root": str(self.assets_root),
        }


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "baseline.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"配置文件 {path} 内容需为字典")
        return data


ENV_OVERRIDE_MAP: Dict[str, Tuple[Sequence[str], Callable[[str], Any]]] = {
    "VIDSYNTH_SEGMENT_FPS": (("segment", "fps_keyframe"), float),
    "VIDSYNTH_THEME_SCORE_THRESHOLD": (("theme_match", "score_threshold"), float),
}


def _apply_env_overrides(data: MutableMapping[str, Any], env: Mapping[str, str]) -> None:
    for env_key, (path, caster) in ENV_OVERRIDE_MAP.items():
        if env_key in env:
            _set_nested_value(data, path, caster(env[env_key]))


def _set_nested_value(target: MutableMapping[str, Any], path: Sequence[str], value: Any) -> None:
    cursor: MutableMapping[str, Any] = target
    *parents, last = path
    for key in parents:
        if key not in cursor or not isinstance(cursor[key], MutableMapping):
            cursor[key] = {}
        cursor = cursor[key]  # type: ignore[assignment]
    cursor[last] = value


def load_config(path: str | Path | None = None, *, env: Mapping[str, str] | None = None) -> PipelineConfig:
    """加载配置：优先显式路径，其次环境变量，最后回退默认 baseline。"""

    env_map = env or os.environ
    config_path = path or env_map.get(CONFIG_ENV_KEY)
    target_path = Path(config_path).expanduser() if config_path else _default_config_path()
    data = _load_yaml(target_path)
    _apply_env_overrides(data, env_map)

    assets_override = env_map.get(ASSETS_ENV_KEY)
    if assets_override:
        data["assets_root"] = str(Path(assets_override).expanduser())

    cfg = PipelineConfig.model_validate({**data, "raw": data})
    return cfg
