"""Embedding 后端：默认实现为均值颜色特征，后续可替换为 CLIP。"""

from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class EmbeddingBackend(Protocol):
    """Embedding 接口，保持简单便于注入真实模型。"""

    emb_model_name: str

    def embed_frame(self, frame: NDArray[np.uint8]) -> NDArray[np.float32]:
        """生成单帧 embedding，返回归一化 float32 向量。"""


class MeanColorEmbedding:
    """极简占位 embedding：使用 RGB 均值，便于本地开发和测试。"""

    emb_model_name = "mean-color-v1"

    def embed_frame(self, frame: NDArray[np.uint8]) -> NDArray[np.float32]:
        mean_rgb = frame.mean(axis=(0, 1))  # type: ignore[arg-type]
        norm = np.linalg.norm(mean_rgb)
        if norm == 0:
            return np.zeros(3, dtype=np.float32)
        return (mean_rgb / norm).astype(np.float32)


DEFAULT_EMBEDDER = MeanColorEmbedding()
