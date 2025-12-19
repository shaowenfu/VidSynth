"""视频关键帧采样。"""

from __future__ import annotations

from pathlib import Path
import math
from typing import Generator, Tuple

import cv2

from .types import FrameSample


class VideoOpenError(RuntimeError):
    """视频无法打开时抛出的异常，便于上层捕获并降级。"""


def iter_keyframes(
    video_path: str | Path,
    target_fps: float,
) -> Generator[FrameSample, None, None]:
    """按目标 FPS 采样关键帧，保持实现简单以便后续替换为更优解码器。"""

    if target_fps <= 0:
        raise ValueError("target_fps must be positive")

    path = Path(video_path)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise VideoOpenError(f"无法打开视频: {path}")

    native_fps = capture.get(cv2.CAP_PROP_FPS) or target_fps
    if native_fps <= 0:
        native_fps = target_fps
    frame_interval = max(int(round(native_fps / target_fps)), 1)

    frame_index = 0
    emitted = 0
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break
            if frame_index % frame_interval == 0:
                timestamp = frame_index / native_fps
                yield FrameSample(
                    video_path=path,
                    frame_index=frame_index,
                    timestamp=timestamp,
                    frame=frame,
                )
                emitted += 1
            frame_index += 1
    finally:
        capture.release()


def estimate_keyframe_count(video_path: str | Path, target_fps: float) -> Tuple[int, float]:
    """估算关键帧采样数与原始 FPS，用于进度近似。"""

    if target_fps <= 0:
        raise ValueError("target_fps must be positive")

    path = Path(video_path)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise VideoOpenError(f"无法打开视频: {path}")

    try:
        native_fps = capture.get(cv2.CAP_PROP_FPS) or target_fps
        if native_fps <= 0:
            native_fps = target_fps
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    finally:
        capture.release()

    frame_interval = max(int(round(native_fps / target_fps)), 1)
    if frame_count <= 0:
        return 0, native_fps
    estimated = int(math.ceil(frame_count / frame_interval))
    return estimated, native_fps
