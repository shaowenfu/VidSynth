"""核心模块入口，聚合数据模型与配置加载工具供各步骤复用。"""

from .datamodels import Clip, ThemePrototype, ThemeQuery, ThemeScore
from .config import PipelineConfig, load_config
from .logging_utils import get_logger, setup_logging
from .paths import resolve_assets_root

__all__ = [
    "Clip",
    "ThemePrototype",
    "ThemeQuery",
    "ThemeScore",
    "PipelineConfig",
    "load_config",
    "get_logger",
    "setup_logging",
    "resolve_assets_root",
]
