"""轻量日志工具，便于后续切换更复杂的观测方案。"""

from __future__ import annotations

import logging
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """设置全局日志级别，默认 INFO，可在 CLI 入口覆盖。"""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取模块专属 logger，抽出来便于后续接入 JSON/结构化日志。"""

    return logging.getLogger(name or "vidsynth")
