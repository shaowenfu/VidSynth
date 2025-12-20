"""轻量日志工具，便于后续切换更复杂的观测方案。"""

from __future__ import annotations

import logging
from typing import Callable, Optional


def setup_logging(level: str = "INFO") -> None:
    """设置全局日志级别，默认 INFO，可在 CLI 入口覆盖。"""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取模块专属 logger，抽出来便于后续接入 JSON/结构化日志。"""

    return logging.getLogger(name or "vidsynth")


class SSELogHandler(logging.Handler):
    """将日志消息转发到 SSE 的 handler（处理器）。"""

    def __init__(self, emit_callback: Callable[[str, logging.LogRecord], None]) -> None:
        super().__init__()
        self._emit_callback = emit_callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            self._emit_callback(message, record)
        except Exception:
            return


def attach_sse_handler(
    logger: logging.Logger,
    emit_callback: Callable[[str, logging.LogRecord], None],
    *,
    level: int = logging.INFO,
) -> logging.Handler:
    """挂载 SSE handler，并返回 handler 以便后续移除。"""

    handler = SSELogHandler(emit_callback)
    handler.setLevel(level)
    logger.addHandler(handler)
    return handler
