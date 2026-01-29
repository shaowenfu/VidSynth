"""Shared runtime state for the server."""

from __future__ import annotations

import threading
from typing import Any, Dict

from vidsynth.core import PipelineConfig, load_config
from vidsynth.theme_match import ThemeMatcher

from .events import EventBroadcaster
from .export_tasks import ExportTaskManager
from .sequence_tasks import SequenceTaskManager
from .settings_store import write_active_settings
from .tasks import TaskManager
from .theme_tasks import ThemeTaskManager

_theme_lock = threading.Lock()
_theme_matcher: ThemeMatcher | None = None


def get_theme_matcher() -> ThemeMatcher:
    global _theme_matcher
    with _theme_lock:
        if _theme_matcher is None:
            config = load_config()
            _theme_matcher = ThemeMatcher(
                embedding_config=config.embedding,
                match_config=config.theme_match,
            )
        return _theme_matcher


def reset_theme_matcher() -> None:
    global _theme_matcher
    with _theme_lock:
        _theme_matcher = None


def apply_settings_bundle(settings: Dict[str, Any]) -> PipelineConfig:
    config_path = write_active_settings(settings)
    config = load_config(config_path)
    task_manager.update_config(config)
    export_task_manager.update_config(config)
    reset_theme_matcher()
    return config


broadcaster = EventBroadcaster()
task_manager = TaskManager(broadcaster)
theme_task_manager = ThemeTaskManager(broadcaster, get_theme_matcher)
sequence_task_manager = SequenceTaskManager(broadcaster)
export_task_manager = ExportTaskManager(broadcaster)
