"""Settings management endpoints."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..settings_store import (
    load_effective_settings,
    load_settings_bundle,
    reset_settings,
    update_settings,
)
from ..state import apply_settings_bundle

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    settings: Dict[str, Any] = Field(default_factory=dict)
    secrets: Dict[str, Any] = Field(default_factory=dict)
    apply: bool = True


@router.get("")
def get_settings() -> Dict[str, Any]:
    return load_settings_bundle()


@router.patch("")
def patch_settings(payload: SettingsPatch) -> Dict[str, Any]:
    bundle = update_settings(settings_patch=payload.settings, secrets_patch=payload.secrets)
    if payload.apply:
        apply_settings_bundle(load_effective_settings())
        bundle["applied"] = True
    else:
        bundle["applied"] = False
    return bundle


@router.post("/apply")
def apply_settings() -> Dict[str, Any]:
    apply_settings_bundle(load_effective_settings())
    return {"status": "ok"}


@router.post("/reset")
def reset_settings_overrides() -> Dict[str, Any]:
    reset_settings()
    apply_settings_bundle(load_effective_settings())
    return load_settings_bundle()
