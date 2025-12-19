"""FastAPI application factory and mounts."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers.assets import router as assets_router
from .routers.segment import router as segment_router
from .state import broadcaster
from .workspace import WORKSPACE_ROOT, ensure_workspace_layout


def create_app() -> FastAPI:
    """Create the FastAPI app instance."""

    ensure_workspace_layout()
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
    app.mount("/static", StaticFiles(directory=str(WORKSPACE_ROOT)), name="static")

    @app.on_event("startup")
    async def _capture_loop() -> None:
        broadcaster.set_loop(asyncio.get_running_loop())

    return app


app = create_app()
