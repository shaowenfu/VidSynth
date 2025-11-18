"""Step2 主题匹配模块入口。"""

from .prototypes import build_theme_query
from .scoring import ThemeMatcher

__all__ = [
    "ThemeMatcher",
    "build_theme_query",
]
