"""核心数据结构定义，覆盖片段、主题原型等最基本实体。"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Sequence


@dataclass(slots=True)
class Clip:
    """描述单个视频片段的结构化信息，保持 JSON 友好以便跨模块传递。"""

    video_id: str
    clip_id: int
    t_start: float
    t_end: float
    fps_keyframe: float
    vis_emb_avg: Sequence[float]
    emb_model: str
    created_at: datetime
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """辅助序列化：方便写入 JSON/EDL 或消息队列。"""

        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["vis_emb_avg"] = list(self.vis_emb_avg)
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Clip":
        """反序列化，默认接受 ISO8601 时间串。"""

        return cls(
            video_id=data["video_id"],
            clip_id=int(data["clip_id"]),
            t_start=float(data["t_start"]),
            t_end=float(data["t_end"]),
            fps_keyframe=float(data["fps_keyframe"]),
            vis_emb_avg=tuple(float(x) for x in data["vis_emb_avg"]),
            emb_model=data["emb_model"],
            created_at=datetime.fromisoformat(data["created_at"]),
            version=int(data.get("version", 1)),
        )


@dataclass(slots=True)
class ThemePrototype:
    """主题原型，封装短语与可选权重，便于后续扩展多模态信息。"""

    text: str
    weight: float = 1.0


@dataclass(slots=True)
class ThemeQuery:
    """封装主题关键词及其正、负原型集合。"""

    theme: str
    positives: List[ThemePrototype] = field(default_factory=list)
    negatives: List[ThemePrototype] = field(default_factory=list)

    @staticmethod
    def from_keywords(theme: str, positives: Sequence[str], negatives: Sequence[str]) -> "ThemeQuery":
        """以字符串列表构建主题查询，后续可扩展到图像/音频原型。"""

        return ThemeQuery(
            theme=theme,
            positives=[ThemePrototype(text=text) for text in positives],
            negatives=[ThemePrototype(text=text) for text in negatives],
        )

    def positive_texts(self) -> List[str]:
        return [proto.text for proto in self.positives]

    def negative_texts(self) -> List[str]:
        return [proto.text for proto in self.negatives]


@dataclass(slots=True)
class ThemeScore:
    """Step2 输出：针对单个 Clip 的主题打分结果。"""

    clip_id: int
    video_id: str
    theme: str
    score: float
    s_pos: float
    s_neg: float
    emb_model: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThemeScore":
        return cls(
            clip_id=int(data["clip_id"]),
            video_id=data["video_id"],
            theme=data["theme"],
            score=float(data["score"]),
            s_pos=float(data["s_pos"]),
            s_neg=float(data["s_neg"]),
            emb_model=data["emb_model"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=dict(data.get("metadata", {})),
        )
