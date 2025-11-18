"""ThemeMatcher 单元测试，验证得分与回退逻辑。"""

from datetime import datetime, timezone
from typing import Dict

import numpy as np
import pytest

from vidsynth.core import Clip, ThemeQuery
from vidsynth.core.config import EmbeddingConfig, ThemeMatchConfig
from vidsynth.theme_match.scoring import ThemeMatcher


class StubTextEncoder:
    text_model_name = "stub"

    def __init__(self, table: Dict[str, np.ndarray]) -> None:
        self.table = table

    def encode_texts(self, texts):  # type: ignore[override]
        return np.stack([self.table[text] for text in texts]).astype(np.float32)


def _make_clip(clip_id: int, vector, emb_model: str = "openclip::ViT-B-32::laion400m_e32") -> Clip:
    return Clip(
        video_id="demo",
        clip_id=clip_id,
        t_start=0.0,
        t_end=1.0,
        fps_keyframe=1.0,
        vis_emb_avg=vector,
        emb_model=emb_model,
        created_at=datetime.now(tz=timezone.utc),
    )


def test_theme_matcher_scores_with_negative_weight():
    encoder = StubTextEncoder(
        {
            "beach": np.array([1.0, 0.0], dtype=np.float32),
            "mountain": np.array([0.0, 1.0], dtype=np.float32),
        }
    )
    matcher = ThemeMatcher(
        embedding_config=EmbeddingConfig(backend="open_clip"),
        match_config=ThemeMatchConfig(negative_weight=0.5),
        text_encoder=encoder,
    )
    clip = _make_clip(0, (1.0, 0.0))
    query = ThemeQuery.from_keywords("beach", ["beach"], ["mountain"])

    scores = matcher.score_clips([clip], query)

    assert len(scores) == 1
    assert scores[0].s_pos == pytest.approx(1.0)
    assert scores[0].s_neg == pytest.approx(0.0)
    assert scores[0].score == pytest.approx(1.0)

    filtered = matcher.filter_scores(scores, threshold=0.5)
    assert len(filtered) == 1
    filtered = matcher.filter_scores(scores, threshold=1.5)
    assert filtered == []


def test_theme_matcher_handles_mean_color_embeddings():
    matcher = ThemeMatcher(
        embedding_config=EmbeddingConfig(),
        match_config=ThemeMatchConfig(),
    )
    clip = _make_clip(1, (0.2, 0.2, 0.2), emb_model="mean-color-v1")
    query = ThemeQuery.from_keywords("beach", ["beach"], [])

    scores = matcher.score_clips([clip], query)

    assert len(scores) == 1
    assert scores[0].score == 0.0
    assert scores[0].metadata["mode"] == "mean_color"
