"""镜头切分逻辑：结合 embedding 与颜色直方图差异。"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import cv2
import numpy as np
from numpy.typing import NDArray

from vidsynth.core.config import SegmentConfig

from .types import EmbeddedSample


def detect_shots(samples: Sequence[EmbeddedSample], config: SegmentConfig) -> List[Tuple[int, int]]:
    """返回 (start_idx, end_idx) 区间列表，end 为开区间。"""

    if not samples:
        return []

    boundaries = [0]
    for idx in range(1, len(samples)):
        emb_dist = _cosine_distance(samples[idx - 1].embedding, samples[idx].embedding)
        hist_diff = _histogram_difference(samples[idx - 1].frame, samples[idx].frame)
        if emb_dist > config.cosine_threshold or hist_diff > config.histogram_threshold:
            boundaries.append(idx)
    boundaries.append(len(samples))
    segments = [(boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)]
    return [segment for segment in segments if segment[1] - segment[0] > 0]


def _cosine_distance(a: NDArray[np.float32], b: NDArray[np.float32]) -> float:
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 1.0
    similarity = float(np.dot(a, b) / (a_norm * b_norm))
    return max(0.0, 1.0 - similarity)


def _histogram_difference(frame_a: NDArray[np.uint8], frame_b: NDArray[np.uint8]) -> float:
    """使用 HSV 直方图的 Bhattacharyya 距离，范围 0-1。"""

    hsv_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2HSV)
    hsv_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2HSV)
    hist_a = cv2.calcHist([hsv_a], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
    hist_b = cv2.calcHist([hsv_b], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
    cv2.normalize(hist_a, hist_a)
    cv2.normalize(hist_b, hist_b)
    distance = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_BHATTACHARYYA)
    return float(min(max(distance, 0.0), 1.0))
