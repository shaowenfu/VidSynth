"""主题打分逻辑，负责将 Clip embedding 与主题原型对齐。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Sequence

import numpy as np
from numpy.typing import NDArray

from vidsynth.core import Clip, ThemeQuery, ThemeScore, get_logger
from vidsynth.core.config import EmbeddingConfig, ThemeMatchConfig

from .encoders import TextEncoder, create_text_encoder


def _normalize_vector(values: Sequence[float]) -> NDArray[np.float32]:
    arr = np.asarray(values, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0.0:
        return arr
    return arr / norm


def _parse_openclip_name(emb_model: str) -> tuple[str, str]:
    parts = emb_model.split("::")
    if len(parts) != 3:
        raise ValueError(f"无法从 emb_model {emb_model} 解析 OpenCLIP 配置")
    _, model_name, pretrained = parts
    return model_name, pretrained


@dataclass
class _ScoreContext:
    emb_model: str
    theme: str


class ThemeMatcher:
    """Step2 核心：根据主题原型为 Clip 计算得分。"""

    def __init__(
        self,
        *,
        embedding_config: EmbeddingConfig,
        match_config: ThemeMatchConfig,
        text_encoder: TextEncoder | None = None,
    ) -> None:
        self.embedding_config = embedding_config
        self.match_config = match_config
        self._text_encoder = text_encoder
        self._encoder_key: str | None = None
        self.logger = get_logger(__name__)

    def score_clips(self, clips: Sequence[Clip], query: ThemeQuery) -> List[ThemeScore]:
        if not clips:
            return []
        if not query.positives and not query.negatives:
            raise ValueError("ThemeQuery 至少需要正向或负向原型")

        self.logger.info("Starting theme matching, theme: '%s', clips count: %d", query.theme, len(clips))
        
        emb_models = {clip.emb_model for clip in clips}
        if len(emb_models) != 1:
            raise ValueError("所有 Clip 必须由同一 embedding 模型生成")
        emb_model = emb_models.pop()
        mode = self._resolve_mode(emb_model)
        context = _ScoreContext(emb_model=emb_model, theme=query.theme)

        if mode == "mean_color":
            self.logger.warning("Clip 使用 mean_color embedding，主题得分将回退为 0。")
            return self._score_mean_color(clips, context)
        if mode != "openclip":
            raise ValueError(f"暂不支持 emb_model={emb_model} 的主题匹配")

        text_encoder = self._ensure_text_encoder(emb_model)
        self.logger.debug("Generating Prompt Embedding: positives=%d, negatives=%d", len(query.positives), len(query.negatives))
        
        results = self._score_openclip(clips, query, context, text_encoder)
        
        if results:
            avg_score = sum(r.score for r in results) / len(results)
            max_score = results[0].score 
            self.logger.info("Matching finished. Max score: %.4f, Avg score: %.4f", max_score, avg_score)
            top3 = [{"id": r.clip_id, "score": r.score} for r in results[:3]]
            self.logger.debug("Top 3 clips: %s", top3)
            
        return results

    def filter_scores(self, scores: Sequence[ThemeScore], threshold: float | None = None) -> List[ThemeScore]:
        if threshold is None:
            return list(scores)
        return [score for score in scores if score.score >= threshold]

    def _ensure_text_encoder(self, emb_model: str) -> TextEncoder:
        if self._text_encoder is not None and (self._encoder_key is None or self._encoder_key == emb_model):
            return self._text_encoder
        model_name, pretrained = _parse_openclip_name(emb_model)
        self.logger.debug("Loading Text Encoder: %s", emb_model)
        encoder = create_text_encoder(
            model_name,
            pretrained,
            device=self.embedding_config.device,
            precision=self.embedding_config.precision,
        )
        self._text_encoder = encoder
        self._encoder_key = emb_model
        return encoder

    def _score_openclip(
        self,
        clips: Sequence[Clip],
        query: ThemeQuery,
        context: _ScoreContext,
        text_encoder: TextEncoder,
    ) -> List[ThemeScore]:
        positive_texts = query.positive_texts() or [query.theme]
        negative_texts = query.negative_texts()

        pos_embs = text_encoder.encode_texts(positive_texts)
        neg_embs = text_encoder.encode_texts(negative_texts) if negative_texts else None

        results: List[ThemeScore] = []
        for clip in clips:
            clip_vec = _normalize_vector(clip.vis_emb_avg)
            s_pos = float(np.max(pos_embs @ clip_vec)) if len(pos_embs) else 0.0
            if neg_embs is not None and len(neg_embs):
                s_neg = float(np.max(neg_embs @ clip_vec))
            else:
                s_neg = 0.0
            score = s_pos - self.match_config.negative_weight * s_neg
            results.append(
                ThemeScore(
                    clip_id=clip.clip_id,
                    video_id=clip.video_id,
                    theme=context.theme,
                    score=score,
                    s_pos=s_pos,
                    s_neg=s_neg,
                    emb_model=context.emb_model,
                    created_at=datetime.now(tz=timezone.utc),
                    metadata={"mode": "openclip"},
                )
            )
        results.sort(key=lambda s: s.score, reverse=True)
        return results

    def _score_mean_color(self, clips: Sequence[Clip], context: _ScoreContext) -> List[ThemeScore]:
        now = datetime.now(tz=timezone.utc)
        return [
            ThemeScore(
                clip_id=clip.clip_id,
                video_id=clip.video_id,
                theme=context.theme,
                score=0.0,
                s_pos=0.0,
                s_neg=0.0,
                emb_model=context.emb_model,
                created_at=now,
                metadata={"mode": "mean_color", "reason": "embedding lacks text alignment"},
            )
            for clip in clips
        ]

    @staticmethod
    def _resolve_mode(emb_model: str) -> str:
        lowered = emb_model.lower()
        if lowered.startswith("mean-color"):
            return "mean_color"
        if lowered.startswith("openclip::"):
            return "openclip"
        return "unknown"
