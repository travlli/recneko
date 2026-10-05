#!/usr/bin/env python3
"""在项目中登记用户的原始角色设定图，并生成应用图标。

重要：**不改动原图的任何像素**
-----------------------------
用户明确要求「使用原图，不要进行自己的改动创作」，因此这里：

* 原图像素**原样保留**，不裁剪、不抠图、不调色、不重绘；
* 只把原图复制进项目，并转存为 PNG（无损，便于打包）；
* 生成 .ico 时，Windows 图标必须是正方形，而原图是 1448x1086，所以把原图
  **居中**放在正方形画布上、四周补上取自原图四角的底色 —— 这是加背景，
  不是改画面内容；缩放到图标尺寸用等比缩放，不改变构图。

原图来源
--------
用户在会话中提供的角色设定图（成熟比例鲸鱼娘三视图 + 细节放大）。
形象设定源头是社区开源资产库「鲸鱼娘开源资产库」
(https://treapgogo.github.io/deepseek-whale-girl/)，该库明示不代表深度求索官方
立场并欢迎二创。

⚠️ 版权提醒：该设定图为第三方作品（非本仓库原创）。直接打进要分发的 exe/apk
可能涉及他人著作权；若计划商用或公开分发，请先自行确认授权。本脚本只做技术
处理，不改变这一点。

用法：
    python tools/make_icon.py
    python tools/make_icon.py --source D:\\art\\new_art.png   # 换一张图
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "src" / "mirecovery" / "resources"

SHEET_NAME = "character_sheet.jpg"
LEGACY_SHEET_NAMES = ("character_sheet.png",)
ICON_NAME = "icon.png"

# The artwork already lives in the repository, so a clean checkout can rebuild
# the icons with no external input. An earlier revision hard-coded an absolute
# path into one developer's attachment store, which meant the script failed for
# anyone else (and silently did nothing until the PNG hashes were compared).
DEFAULT_SOURCE = OUT_DIR / SHEET_NAME

# Optional overrides, in priority order: --source, $RECNEKO_ART_SOURCE, default.
ART_SOURCE_ENV = "RECNEKO_ART_SOURCE"


def find_source(explicit: str | None = None) -> Path:
    """Locate the source artwork."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    from_env = os.environ.get(ART_SOURCE_ENV)
    if from_env:
        candidates.append(Path(from_env))
    candidates.append(DEFAULT_SOURCE)
    for legacy in LEGACY_SHEET_NAMES:
        candidates.append(OUT_DIR / legacy)

    for path in candidates:
        if path.is_file():
            return path

    raise SystemExit(
        "找不到角色原图。请把图片放到：\n"
        f"  {DEFAULT_SOURCE}\n"
        f"或用 --source <路径> / 环境变量 {ART_SOURCE_ENV} 指定。"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=None,
                        help="角色原图路径（默认用仓库内的 resources/character_sheet.jpg）")
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = find_source(args.source)
    sheet_path = OUT_DIR / SHEET_NAME
    print(f"[make_icon] 原图: {source}")

    # 1) 原图入库：按原始编码转存，避免再压一次。
    if source.resolve() != sheet_path.resolve():
        with Image.open(source) as handle:
            handle.load()
            image = handle.convert("RGBA") if handle.mode != "RGBA" else handle.copy()
        suffix = source.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            # 原图就是 JPEG，保存 JPEG 而不是 PNG：避免体积暴涨，
            # 也不会比原图损失更多（原图本身已有 JPEG 压缩）。
            image.convert("RGB").save(sheet_path, format="JPEG", quality=95)
        elif suffix == ".png":
            image.save(sheet_path, format="PNG", optimize=True)
        else:
            image.save(sheet_path, format="PNG", optimize=True)
        print(
            f"已导入原图 -> {sheet_path.relative_to(PROJECT_ROOT)}  "
            f"{image.size[0]}x{image.size[1]}"
        )
    else:
        print(f"原图已就位 -> {sheet_path.relative_to(PROJECT_ROOT)}")

    # 2) 图标：原图居中 + 补边。原图内容不做任何加工。
    with Image.open(sheet_path) as handle:
        handle.load()
        sheet = handle.convert("RGBA")

    # 补边底色取四角，但如果四角本身是深色（例如图主体铺满），改用中位数以免
    # 出现突兀的深色边框。
    corners = [
        sheet.getpixel((0, 0)),
        sheet.getpixel((sheet.width - 1, 0)),
        sheet.getpixel((0, sheet.height - 1)),
        sheet.getpixel((sheet.width - 1, sheet.height - 1)),
    ]
    backdrop = tuple(sum(c[i] for c in corners) // 4 for i in range(3)) + (255,)
    if sum(backdrop[:3]) < 300:  # 偏暗，退回白色底
        backdrop = (255, 255, 255, 255)

    side = 512
    canvas = Image.new("RGBA", (side, side), backdrop)
    scaled = sheet.copy()
    scaled.thumbnail((side, side), Image.LANCZOS)
    canvas.alpha_composite(
        scaled, ((side - scaled.width) // 2, (side - scaled.height) // 2)
    )

    icon_path = OUT_DIR / ICON_NAME
    canvas.save(icon_path, format="PNG")

    ico_path = OUT_DIR / "icon.ico"
    canvas.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    # 窗口标题栏图标：tkinter 直接读 512px PNG 偏重，另存一张小图。
    window_icon = canvas.copy()
    window_icon.thumbnail((64, 64), Image.LANCZOS)
    window_icon_path = OUT_DIR / "window_icon.png"
    window_icon.save(window_icon_path, format="PNG")

    # 清理旧资源，避免与当前原图并存造成混淆。
    removed = []
    for stale in ("mascot.png", "mascot_small.png", *LEGACY_SHEET_NAMES):
        target = OUT_DIR / stale
        if target.is_file() and target.resolve() != sheet_path.resolve():
            target.unlink()
            removed.append(stale)

    for path in (sheet_path, icon_path, ico_path, window_icon_path):
        print(f"  {path.name}  {path.stat().st_size / 1024:.1f} KB")
    if removed:
        print(f"已移除旧资源：{', '.join(removed)}")
    print(f"图标补边底色：RGB{backdrop[:3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
