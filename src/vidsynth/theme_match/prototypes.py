"""主题原型生成：使用 Deepseek 模型扩展正/负提示词。"""

from __future__ import annotations

import json
import os
import re
from typing import Iterable, List, Sequence, Tuple

import httpx

from vidsynth.core import ThemeQuery

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
_CODE_BLOCK_PATTERN = re.compile(r"^```(?:json)?\s*(?P<body>.+?)\s*```$", re.DOTALL)


def build_theme_query(theme: str, positives: Sequence[str] | None = None, negatives: Sequence[str] | None = None) -> ThemeQuery:
    """根据主题构建 ThemeQuery，优先调用 Deepseek，大模型不可用时回退到固定模板。"""

    user_pos = list(positives or [])
    user_neg = list(negatives or [])
    llm_pos, llm_neg = _generate_with_deepseek(theme)

    merged_pos = _unique_keep_order(user_pos + llm_pos)
    merged_neg = _unique_keep_order(user_neg + llm_neg)

    if not merged_pos:
        merged_pos = _fallback_prototypes(theme)[0]
    return ThemeQuery.from_keywords(theme=theme, positives=merged_pos, negatives=merged_neg)


def _generate_with_deepseek(theme: str) -> Tuple[List[str], List[str]]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return _fallback_prototypes(theme)

    prompt = (
        "你是视频素材筛选助手。请针对主题 "
        f"{theme!r} 给出 5 个简洁的英文正向关键词和 4 个对照关键词。"
        "关键词应为单词或短词组，避免完整句子。对照关键词用于排除与主题无关的内容。"
        "仅输出 JSON，格式：{" "\"positives\":[...],\"negatives\":[...]" "}."
    )
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You generate short English prompts for video retrieval."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 3000,
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                DEEPSEEK_API_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return _fallback_prototypes(theme)

    content = _extract_content(data)
    if not content:
        return _fallback_prototypes(theme)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return _fallback_prototypes(theme)

    pos = [str(item).strip() for item in parsed.get("positives", []) if str(item).strip()]
    neg = [str(item).strip() for item in parsed.get("negatives", []) if str(item).strip()]
    if not pos and not neg:
        return _fallback_prototypes(theme)
    return pos, neg


def _extract_content(data: dict) -> str | None:
    choices = data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message", {})
    content = (message.get("content") or "").strip()
    if not content:
        return None
    match = _CODE_BLOCK_PATTERN.match(content)
    if match:
        return match.group("body").strip()
    return content


def _fallback_prototypes(theme: str) -> Tuple[List[str], List[str]]:
    base_theme = theme.strip().lower() or "scene"
    positives = [
        base_theme,
        "closeup",
        "detail",
        "motion",
        "product",
    ]
    negatives = [
        "city",
        "office",
        "night",
        "snow",
    ]
    return positives, negatives


def _unique_keep_order(items: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result
