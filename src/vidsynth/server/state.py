"""Shared runtime state for the server."""

from __future__ import annotations

import threading

from vidsynth.core import load_config
from vidsynth.theme_match import ThemeMatcher

from .events import EventBroadcaster
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

broadcaster = EventBroadcaster()
task_manager = TaskManager(broadcaster)
theme_task_manager = ThemeTaskManager(broadcaster, get_theme_matcher)
