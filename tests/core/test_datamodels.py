"""核心数据模型测试，确保序列化/构造器稳定。"""

from datetime import datetime, timezone

from vidsynth.core import Clip, ThemeQuery


def test_clip_roundtrip() -> None:
    clip = Clip(
        video_id="vid-001",
        clip_id=12,
        t_start=1.5,
        t_end=4.2,
        fps_keyframe=1.0,
        vis_emb_avg=(0.1, 0.2, 0.3),
        emb_model="clip-vit-b/32",
        created_at=datetime.now(tz=timezone.utc),
        version=1,
    )

    payload = clip.to_dict()
    restored = Clip.from_dict(payload)

    assert restored == clip


def test_theme_query_from_keywords() -> None:
    query = ThemeQuery.from_keywords(
        theme="beach",
        positives=["sandy beach", "ocean shore"],
        negatives=["snow mountain"],
    )

    assert query.positive_texts() == ["sandy beach", "ocean shore"]
    assert query.negative_texts() == ["snow mountain"]
    assert query.theme == "beach"
