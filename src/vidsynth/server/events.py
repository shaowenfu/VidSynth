"""Server-Sent Events helpers."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, AsyncGenerator, Iterable

from fastapi import Request


class EventBroadcaster:
    """In-memory broadcaster for SSE subscribers."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, message: dict[str, Any]) -> None:
        if not self._loop:
            return
        with self._lock:
            queues = list(self._subscribers)
        for queue in queues:
            asyncio.run_coroutine_threadsafe(queue.put(message), self._loop)


def _format_sse(message: dict[str, Any]) -> str:
    payload = json.dumps(message, ensure_ascii=False)
    return f"data: {payload}\n\n"


async def stream_events(
    request: Request,
    broadcaster: EventBroadcaster,
    *,
    initial_messages: Iterable[dict[str, Any]] = (),
) -> AsyncGenerator[str, None]:
    queue = await broadcaster.subscribe()
    try:
        for message in initial_messages:
            yield _format_sse(message)
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield _format_sse(message)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        broadcaster.unsubscribe(queue)
