"""/rec检查喵/ —— 小米 / 红米刷机报错检查助手。

日志分析 + 本地知识库检索 + 界面截图识别，覆盖
MediaTek / 高通 / fastboot / recovery / AVB 常见报错。
"""

from . import theme
from .kb import KB, Entry, Match
from .report import build_report, render
from .scanner import Finding, analyze

__version__ = "2.0.0"
__app_name__ = theme.APP_DISPLAY_NAME

__all__ = [
    "KB",
    "Entry",
    "Match",
    "Finding",
    "analyze",
    "build_report",
    "render",
    "theme",
    "__version__",
    "__app_name__",
]
