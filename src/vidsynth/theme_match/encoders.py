"""文本编码后端：与 Step1 的视觉 embedding 对齐。"""

from __future__ import annotations

from typing import Protocol, Sequence

import numpy as np
from numpy.typing import NDArray

try:  # 与 segment.embedding 保持一致的延迟导入策略
    import open_clip  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - 未安装 open_clip
    open_clip = None

import torch
import torch.nn.functional as F


class TextEncoder(Protocol):
    """文本编码协议，用于将主题原型转为与 Clip 向量对齐的特征。"""

    text_model_name: str

    def encode_texts(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """批量编码文本，返回 L2 归一化后的特征矩阵。"""


class OpenClipTextEncoder:
    """OpenCLIP 文本编码封装。"""

    def __init__(self, model_name: str, pretrained: str, *, device: str = "cpu", precision: str = "fp32") -> None:
        if open_clip is None:
            raise RuntimeError("open-clip-torch 未安装，无法执行主题匹配")

        self.device = torch.device(device)
        self.model, _, _ = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
            device=device,
        )
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer(model_name)
        self.precision = precision
        self.text_model_name = f"openclip::{model_name}::{pretrained}"

    def encode_texts(self, texts: Sequence[str]) -> NDArray[np.float32]:  # type: ignore[override]
        if not texts:
            raise ValueError("encode_texts requires at least one text prompt")
        tokens = self.tokenizer(list(texts)).to(self.device)
        context = torch.inference_mode if hasattr(torch, "inference_mode") else torch.no_grad
        with context():  # type: ignore[misc]
            feats = self.model.encode_text(tokens)
        feats = F.normalize(feats, dim=-1)
        return feats.to("cpu", dtype=torch.float32).numpy()


def create_text_encoder(model_name: str, pretrained: str, *, device: str, precision: str) -> TextEncoder:
    """根据指定模型构造文本编码器。"""

    return OpenClipTextEncoder(
        model_name=model_name,
        pretrained=pretrained,
        device=device,
        precision=precision,
    )
