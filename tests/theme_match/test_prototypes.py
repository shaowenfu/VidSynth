"""Deepseek 原型构造测试，验证回退与解析逻辑。"""

import json
from types import SimpleNamespace

import pytest

from vidsynth.theme_match.prototypes import build_theme_query


def test_build_theme_query_fallback(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    query = build_theme_query("beach sunset")

    assert query.positive_texts()
    assert query.negative_texts()


def test_build_theme_query_deepseek(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")

    class DummyResponse:
        def __init__(self):
            self._data = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "positives": ["a snowy beach"],
                                    "negatives": ["busy highway"],
                                }
                            )
                        }
                    }
                ]
            }

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class DummyClient:
        def __init__(self, *_, **__):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *_, **__):
            return DummyResponse()

    monkeypatch.setattr("vidsynth.theme_match.prototypes.httpx.Client", DummyClient)

    query = build_theme_query("snow beach", positives=["user prompt"], negatives=[])  # type: ignore[arg-type]

    assert "user prompt" in query.positive_texts()
    assert "a snowy beach" in query.positive_texts()
    assert query.negative_texts() == ["busy highway"]
