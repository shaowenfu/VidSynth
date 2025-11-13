"""路径工具：集中处理资源目录，方便未来迁移。"""

from __future__ import annotations

import os
from pathlib import Path


ASSETS_ENV_KEY = "VIDSYNTH_STORAGE_ROOT"


def resolve_assets_root(default: Path | None = None) -> Path:
    """根据环境变量或默认值确定素材根目录。"""

    env_value = os.getenv(ASSETS_ENV_KEY)
    if env_value:
        return Path(env_value).expanduser().resolve()
    if default is not None:
        return default.expanduser().resolve()
    # 默认回退到仓库内的 assets 目录，保持简单可用
    return Path(__file__).resolve().parents[2] / "assets"
