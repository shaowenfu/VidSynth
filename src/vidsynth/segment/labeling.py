"""片段标签化接口：当前仅定义协议，后续可接入本地或云端模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, Sequence

import numpy as np
from numpy.typing import NDArray

from vidsynth.core import Clip


@dataclass(slots=True)
class LabelResult:
    """描述单个 Clip 的标签产物，可扩展附加评分/置信度。"""

    clip_id: int
    labels: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class LabelBackend(Protocol):
    """标签后端协议：可由本地模型或云端 API 实现。"""

    backend_name: str

    def label_clip(
        self,
        clip: Clip,
        frames: Sequence[NDArray[np.uint8]],
    ) -> LabelResult:
        """根据 Clip 代表帧生成标签；frames 允许后续传多帧。"""

        ...
