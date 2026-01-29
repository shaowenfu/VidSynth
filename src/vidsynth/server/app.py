"""FastAPI application factory and mounts."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from vidsynth.core import attach_sse_handler, get_logger, setup_logging
from vidsynth.core.logging_utils import get_stage_name

from .routers.assets import router as assets_router
from .routers.segment import router as segment_router
from .routers.settings import router as settings_router
from .routers.theme import router as theme_router
from .routers.sequence import router as sequence_router
from .routers.export import router as export_router
from .settings_store import load_effective_settings
from .state import apply_settings_bundle, broadcaster
from .workspace import WORKSPACE_ROOT, ensure_workspace_layout


def _global_log_listener(message: str, record: logging.LogRecord) -> None:
    """全局日志监听器，将日志转发到 SSE。"""
    log_entry = {
        "type": "log",
        "level": record.levelname,
        "stage": get_stage_name(record.name),
        "message": message,
        "timestamp": datetime.fromtimestamp(record.created).isoformat(),
        "context": getattr(record, "context", {}),
        "module": record.name,
    }
    broadcaster.publish(log_entry)


def create_app() -> FastAPI:
    """Create the FastAPI app instance."""

    ensure_workspace_layout()
    # 确保日志系统初始化，默认级别 INFO
    setup_logging(level="INFO")
    # 显式设置 vidsynth logger 级别，确保 SSE Handler 能接收到 INFO 消息
    root_logger = get_logger()
    root_logger.setLevel(logging.INFO)

    app = FastAPI(title="VidSynth Server", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    app.include_router(assets_router)
    app.include_router(segment_router)
    app.include_router(settings_router)
    app.include_router(theme_router)
    app.include_router(sequence_router)
    app.include_router(export_router)
    app.mount("/static", StaticFiles(directory=str(WORKSPACE_ROOT)), name="static")

    @app.on_event("startup")
    async def _capture_loop() -> None:
        broadcaster.set_loop(asyncio.get_running_loop())
        apply_settings_bundle(load_effective_settings())
        # 挂载全局 SSE 日志监听器
        attach_sse_handler(root_logger, _global_log_listener)
        # 发送一条测试日志
        root_logger.info("VidSynth Server started. Logging system initialized.")

    return app


app = create_app()
