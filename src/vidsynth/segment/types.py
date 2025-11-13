"""细分阶段内部使用的结构体。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from numpy.typing import NDArray


@dataclass(slots=True)
class FrameSample:
    """关键帧采样结果，包含帧索引、时间戳以及原始像素。"""

    video_path: Path
    frame_index: int
    timestamp: float
    frame: NDArray[np.uint8]


@dataclass(slots=True)
class EmbeddedSample:
    """关键帧加上 embedding，便于后续 shot detection 直接消费。"""

    sample: FrameSample
    embedding: NDArray[np.float32]

    @property
    def timestamp(self) -> float:
        return self.sample.timestamp

    @property
    def frame(self) -> NDArray[np.uint8]:
        return self.sample.frame
