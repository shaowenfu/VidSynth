"""Settings storage and merge helpers."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import yaml

from vidsynth.core.config import CONFIG_ENV_KEY

from .workspace import CONFIGS_DIR

BASELINE_CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "baseline.yaml"
OVERRIDE_CONFIG_PATH = CONFIGS_DIR / "override.yaml"
ACTIVE_CONFIG_PATH = CONFIGS_DIR / "active.yaml"
SECRETS_PATH = CONFIGS_DIR / "secrets.json"

SECRET_PATHS: Tuple[Tuple[str, ...], ...] = (
    ("llm", "api_key"),
    ("llm", "openai_api_key"),
    ("llm", "deepseek_api_key"),
)

DEFAULT_SETTINGS: Dict[str, Any] = {
    "sequence": {
        "threshold_upper": 0.2,
        "threshold_lower": 0.15,
        "min_duration": 2.0,
        "max_duration": 6.0,
        "merge_gap": 1.0,
    },
    "cluster": {
        "max_clusters": 20,
        "representative_count": 5,
    },
    "llm": {
        "provider": "deepseek",
        "base_url": "",
        "model": "",
        "api_key": "",
        "temperature": 0.3,
        "timeout_s": 60,
    },
    "prompts": {
        "expand": {
            "template": "Expand theme: {theme}",
            "negative_hint": "Avoid abstract or multi-word sentences.",
        }
    },
}


def load_effective_settings() -> Dict[str, Any]:
    """Load baseline + override + secrets and return merged settings."""

    baseline = _read_yaml(BASELINE_CONFIG_PATH)
    override = _read_yaml(OVERRIDE_CONFIG_PATH)
    secrets = _read_json(SECRETS_PATH)

    effective = _deep_merge(DEFAULT_SETTINGS, baseline)
    effective = _deep_merge(effective, override)
    return _merge_secrets(effective, secrets)


def load_settings_bundle() -> Dict[str, Any]:
    """Load baseline + override + secrets and return masked bundle for clients."""

    override = _read_yaml(OVERRIDE_CONFIG_PATH)
    secrets = _read_json(SECRETS_PATH)
    effective = load_effective_settings()
    masked = _mask_secrets(deepcopy(effective), secrets)
    secret_flags = _build_secret_flags(secrets)
    return {
        "settings": masked,
        "override": override,
        "has_secrets": secret_flags,
        "paths": {
            "baseline": str(BASELINE_CONFIG_PATH),
            "override": str(OVERRIDE_CONFIG_PATH),
            "active": str(ACTIVE_CONFIG_PATH),
        },
    }


def update_settings(
    *,
    settings_patch: Dict[str, Any],
    secrets_patch: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    override = _read_yaml(OVERRIDE_CONFIG_PATH)
    cleaned_patch, extracted_secrets = _extract_secrets(settings_patch)
    override = _deep_merge(override, cleaned_patch)
    _write_yaml(OVERRIDE_CONFIG_PATH, override)

    secrets = _read_json(SECRETS_PATH)
    secrets = _deep_merge(secrets, secrets_patch or {})
    secrets = _deep_merge(secrets, extracted_secrets)
    secrets = _prune_empty(secrets)
    _write_json(SECRETS_PATH, secrets)
    return load_settings_bundle()


def reset_settings() -> None:
    if OVERRIDE_CONFIG_PATH.exists():
        OVERRIDE_CONFIG_PATH.unlink()
    if SECRETS_PATH.exists():
        SECRETS_PATH.unlink()


def write_active_settings(settings: Dict[str, Any]) -> Path:
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    _write_yaml(ACTIVE_CONFIG_PATH, settings)
    os.environ[CONFIG_ENV_KEY] = str(ACTIVE_CONFIG_PATH)
    return ACTIVE_CONFIG_PATH


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            return {}
        return data


def _write_yaml(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = deepcopy(value)
    return merged


def _set_nested(target: Dict[str, Any], path: Iterable[str], value: Any) -> None:
    cursor = target
    *parents, last = list(path)
    for key in parents:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    cursor[last] = value


def _pop_nested(target: Dict[str, Any], path: Iterable[str]) -> Any:
    cursor = target
    *parents, last = list(path)
    for key in parents:
        if key not in cursor or not isinstance(cursor[key], dict):
            return None
        cursor = cursor[key]
    return cursor.pop(last, None)


def _extract_secrets(settings_patch: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    patch_copy = deepcopy(settings_patch)
    secrets: Dict[str, Any] = {}
    for path in SECRET_PATHS:
        value = _pop_nested(patch_copy, path)
        if value not in (None, ""):
            _set_nested(secrets, path, value)
    return patch_copy, secrets


def _merge_secrets(settings: Dict[str, Any], secrets: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(settings)
    return _deep_merge(merged, secrets)


def _mask_secrets(settings: Dict[str, Any], secrets: Dict[str, Any]) -> Dict[str, Any]:
    for path in SECRET_PATHS:
        cursor = settings
        for key in path[:-1]:
            if key not in cursor or not isinstance(cursor[key], dict):
                cursor = None
                break
            cursor = cursor[key]
        if cursor is None:
            continue
        last = path[-1]
        if last in cursor:
            cursor[last] = "***"
    if secrets:
        for path in SECRET_PATHS:
            cursor = settings
            for key in path[:-1]:
                if key not in cursor or not isinstance(cursor[key], dict):
                    cursor = None
                    break
                cursor = cursor[key]
            if cursor is None:
                continue
            last = path[-1]
            if last in cursor and cursor[last] == "":
                cursor[last] = "***"
    return settings


def _build_secret_flags(secrets: Dict[str, Any]) -> Dict[str, bool]:
    flags: Dict[str, bool] = {}
    for path in SECRET_PATHS:
        cursor: Any = secrets
        for key in path:
            if not isinstance(cursor, dict) or key not in cursor:
                cursor = None
                break
            cursor = cursor[key]
        flags[".".join(path)] = bool(cursor)
    return flags


def _prune_empty(data: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            nested = _prune_empty(value)
            if nested:
                cleaned[key] = nested
        elif value not in (None, ""):
            cleaned[key] = value
    return cleaned
