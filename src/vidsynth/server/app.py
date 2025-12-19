"""FastAPI application factory and mounts."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers.assets import router as assets_router
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
    app.mount("/static", StaticFiles(directory=str(WORKSPACE_ROOT)), name="static")
    return app


app = create_app()
