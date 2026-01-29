"""路径工具：集中处理资源目录，方便未来迁移。"""

from __future__ import annotations

import os
from pathlib import Path


ASSETS_ENV_KEY = "VIDSYNTH_STORAGE_ROOT"
WORKSPACE_ENV_KEY = "VIDSYNTH_WORKSPACE_ROOT"


def resolve_assets_root(default: Path | None = None) -> Path:
    """根据环境变量或默认值确定素材根目录。"""

    env_value = os.getenv(ASSETS_ENV_KEY)
    if env_value:
        return Path(env_value).expanduser().resolve()
    if default is not None:
        return default.expanduser().resolve()
    workspace_override = os.getenv(WORKSPACE_ENV_KEY)
    if workspace_override:
        return (Path(workspace_override).expanduser().resolve() / "videos")
    # 默认回退到仓库内的 workspace/videos，保持与运行时一致
    return Path(__file__).resolve().parents[3] / "workspace" / "videos"
