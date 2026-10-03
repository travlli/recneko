"""二次元主题：配色、字体与吉祥物路径.

集中放在这里，避免界面里散落颜色字面量。主题是「樱花粉 + DeepSeek 蓝」，
与 tools/make_icon.py 里的调色板保持一致（图标由同一套色值绘制）。

界面用的是 tkinter，配色直接通过 tk 的 widget 选项生效，所以这里返回的是
十六进制字符串；Pillow 绘制图标用的是 RGBA 元组。
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# 应用标识
# --------------------------------------------------------------------------

# 显示用的正式名称。前后加斜杠是刻意的「命令风」写法。
APP_DISPLAY_NAME = "/rec检查喵/"
APP_SHORT_NAME = "rec检查喵"
APP_ID = "com.dsh.recneko"

# 内置吉祥物：社区俗称「大肥鱼」，设定为蓝色鲸鱼娘。
# 形象由 tools/make_icon.py 用代码重绘（设定要素取自社区开源资产库，见该脚本
# 顶部说明；未使用该站任何图片文件）。
CHARACTER_NAME = "鲸鱼娘"
CHARACTER_ALIAS = "大肥鱼"

# 文件/可执行文件用的安全名称（不含斜杠，Windows 文件名不能带 / ）
EXE_BASENAME = "rec检查喵"
EXE_BASENAME_ASCII = "RecNeko"

# --------------------------------------------------------------------------
# 配色：深蓝（navy）主调 + 蕾丝白 + 亮蓝 + 少量金
# 与 tools/make_icon.py 共用同一套设定（成熟比例设定图的配色）
# --------------------------------------------------------------------------

# 主色
NAVY_DEEP = "#121e44"       # 最深：标题、按钮文字
NAVY = "#203474"            # 主深蓝：主按钮底、强调
NAVY_MID = "#385cb2"
BLUE = "#4a8ce8"            # 亮蓝
BLUE_LIGHT = "#84c4f2"      # 浅海蓝
BLUE_PALE = "#cfe4fb"       # 极浅蓝：次按钮底

# 金色点缀（宝石边框、十字星、纽扣）
GOLD = "#e8c476"
GOLD_DEEP = "#c49e4e"

# 中性
BG = "#f2f6fd"              # 页面底色：冷白偏蓝
CARD = "#ffffff"
CARD_ALT = "#eaf1fd"        # 次级卡片：淡蓝
INK = "#1c2748"             # 正文
INK_SOFT = "#5c6a8c"        # 次要文字
LINE = "#d4e0f4"            # 分隔线
OK = "#3fae7a"
WARN = "#e08b2e"

# 等宽字体区域用的底色（日志输入、结果区）
CODE_BG = "#fbfdff"

# 界面 emoji 装饰。tkinter 在 Windows 上能显示彩色 emoji，缺字体时会退化成
# 方块，所以这些只用于装饰，不承载信息。
DECOR = {
    "whale": "🐳",
    "cat": "🐱",
    "sparkle": "✨",
    "heart": "💙",
    "fish": "🐟",
    "paw": "🐾",
    "search": "🔍",
    "image": "🖼",
    "gem": "💎",
}

# --------------------------------------------------------------------------
# 字体
# --------------------------------------------------------------------------

CJK_FONTS = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "PingFang SC",
)
ROUND_FONTS = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "YouYuan",          # 幼圆，二次元界面常用
    "SimHei",
)
MONO_FONTS = (
    "Cascadia Mono",
    "Consolas",
    "Sarasa Mono SC",
    "Courier New",
)

# --------------------------------------------------------------------------
# 资源
# --------------------------------------------------------------------------

RESOURCES = Path(__file__).resolve().parent / "resources"
ICON_PNG = RESOURCES / "icon.png"
# 窗口标题栏用的小尺寸图标（由 tools/make_icon.py 生成）
WINDOW_ICON_PNG = RESOURCES / "window_icon.png"
# 应用内展示的是**用户提供的原图**，不做裁剪或改写。
# 当前为 Q 版（三头身）鲸鱼娘立绘；早期用过程序绘制形象与成熟比例设定图，
# 均已按用户要求替换。
SHEET_IMAGE = RESOURCES / "character_sheet.jpg"


def sheet_candidates() -> list[Path]:
    """设定图的候选路径（冻结打包后位置会变）。"""
    import sys

    candidates: list[Path] = [SHEET_IMAGE]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base = Path(meipass) / "mirecovery" / "resources"
        candidates = [base / SHEET_IMAGE.name] + candidates
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "mirecovery" / "resources" / SHEET_IMAGE.name)
        candidates.append(
            exe_dir / "_internal" / "mirecovery" / "resources" / SHEET_IMAGE.name
        )
    return candidates


def find_sheet() -> Path | None:
    """返回第一个存在的设定图。"""
    for path in sheet_candidates():
        if path.is_file():
            return path
    return None




# 界面文案里反复出现的吉祥物口吻
def greeting() -> str:
    return f"{DECOR['whale']} 我是{CHARACTER_NAME}（{CHARACTER_ALIAS}），把报错丢给我，喵～"


def analyzing() -> str:
    return f"{DECOR['search']} {CHARACTER_NAME}正在翻知识库…"


def found(count: int) -> str:
    if count <= 0:
        return f"{DECOR['cat']} 这个问题喵也没见过…换个说法再试试？"
    return f"{DECOR['sparkle']} 找到 {count} 条线索，喵！"


def not_found() -> str:
    return f"{DECOR['cat']} 这张图喵也认不出来…把报错文字粘进来试试？"
