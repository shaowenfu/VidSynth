"""Embedding 后端：提供均值颜色占位实现与 OpenCLIP 封装。"""

from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray

try:  # 延迟导入，避免无 GPU 环境报错
    import open_clip  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - 在未安装 open_clip 的环境下执行
    open_clip = None

import torch
import torch.nn.functional as F

try:  # Pillow 可选依赖，仅在使用 OpenCLIP 时需要
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover
    Image = None

from vidsynth.core.config import EmbeddingConfig

OPEN_CLIP_PRESETS = {
    "cpu-small": ("ViT-B-32", "laion400m_e32"),
    "gpu-large": ("ViT-H-14", "laion2b_s32b_b79k"),
}


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


class OpenClipEmbedding:
    """OpenCLIP 封装，支持 CPU 小模型与 GPU 大模型切换。"""

    def __init__(
        self,
        model_name: str,
        pretrained: str,
        device: str = "cpu",
        precision: str = "fp32",
    ) -> None:
        if open_clip is None:
            raise RuntimeError("open-clip-torch 未安装，无法使用 OpenCLIP 模式")
        if Image is None:
            raise RuntimeError("Pillow 未安装，无法使用 OpenCLIP 模式")

        self.device = torch.device(device)
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
            device=device,
        )
        self.model.eval()
        self.precision = precision
        self.emb_model_name = f"openclip::{model_name}::{pretrained}"

    def embed_frame(self, frame: NDArray[np.uint8]) -> NDArray[np.float32]:
        rgb = frame[..., ::-1]  # BGR -> RGB
        image = Image.fromarray(rgb)
        tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        if self.precision.lower() != "fp32" and self.device.type != "cpu":
            tensor = tensor.half()
        context = torch.inference_mode if hasattr(torch, "inference_mode") else torch.no_grad
        with context():  # type: ignore[misc]
            feats = self.model.encode_image(tensor)
        feats = F.normalize(feats, dim=-1)
        return feats.squeeze(0).to("cpu", dtype=torch.float32).numpy()


def create_embedder(config: EmbeddingConfig) -> EmbeddingBackend:
    """根据配置创建 embedder，默认回退到均值颜色。"""

    backend = config.backend.lower()
    if backend == "open_clip":
        model_name = config.model_name
        pretrained = config.pretrained
        if config.preset:
            preset_key = config.preset.lower()
            if preset_key not in OPEN_CLIP_PRESETS:
                raise ValueError(f"未知 OpenCLIP 预设: {config.preset}")
            model_name, pretrained = OPEN_CLIP_PRESETS[preset_key]
        return OpenClipEmbedding(
            model_name=model_name,
            pretrained=pretrained,
            device=config.device,
            precision=config.precision,
        )
    if backend == "mean_color":  # 默认路径
        return MeanColorEmbedding()
    raise ValueError(f"未知 embedding backend: {config.backend}")
