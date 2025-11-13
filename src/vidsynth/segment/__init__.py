"""Step2: 片段切分模块，聚合关键帧采样、embedding 与剪辑逻辑。"""

from .clipper import build_clips_from_samples, segment_video
from .embedding import EmbeddingBackend, MeanColorEmbedding, create_embedder
from .labeling import LabelBackend, LabelResult
from .loader import FrameSample, iter_keyframes
from .types import EmbeddedSample

__all__ = [
    "segment_video",
    "build_clips_from_samples",
    "FrameSample",
    "EmbeddedSample",
    "EmbeddingBackend",
    "MeanColorEmbedding",
    "create_embedder",
    "LabelBackend",
    "LabelResult",
    "iter_keyframes",
]
