"""Shared runtime state for the server."""

from __future__ import annotations

from .events import EventBroadcaster
from .tasks import TaskManager

broadcaster = EventBroadcaster()
task_manager = TaskManager(broadcaster)
