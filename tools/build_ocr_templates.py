#!/usr/bin/env python3
"""Render OCR character templates from system fonts into a bundled data file.

Why templates instead of a real OCR engine
------------------------------------------
Android builds use Chaquopy, whose package set has no Tesseract (a C++ binary)
and no onnxruntime - so PaddleOCR / RapidOCR / pytesseract cannot ship in the
apk. A pure-Pillow recogniser is the only thing that works on every target.

It also means the runtime needs no fonts: templates are rendered here, at build
time, and bundled as ``src/mirecovery/data/ocr_templates.json``. On Android the
system fonts differ from Windows, so rendering at runtime would be wrong anyway.

Output format: each glyph is a normalised 16x24 greyscale bitmap, zlib+base64
encoded (same trick as the image reference library - a raw JSON list of numbers
would be ~100x larger).

    python tools/build_ocr_templates.py
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mirecovery.ocr import (  # noqa: E402
    CHAR_HEIGHT,
    CHAR_WIDTH,
    TEMPLATE_VERSION,
    normalize_glyph,
)

OUT = PROJECT_ROOT / "src" / "mirecovery" / "data" / "ocr_templates.json"

# Fonts to render templates from. Several families and both weights, because a
# screenshot's font is unknown and a single font's templates do not transfer.
FONT_FILES = [
    "consola.ttf", "consolab.ttf",
    "cour.ttf",
    "arial.ttf", "arialbd.ttf",
    "segoeui.ttf",
    "tahoma.ttf",
    "verdana.ttf",
    "lucon.ttf",          # Lucida Console
    "micross.ttf",        # Microsoft Sans Serif
]

DIGITS = "0123456789"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
PUNCT = ":./\\-_()[]<>,;'\"=+*#%!?@&|~^$"

# Render each glyph at many sizes.
#
# This is essential, not a refinement. Normalisation scales each glyph to fit the
# template grid, so a glyph's proportions depend on the size it was rendered at -
# the same "0" rendered at 64px and at 22px only correlate at 0.76. With
# single-size templates a *wrong* character often outscored the right one
# (measured: 91.5% on digits, 70% on whole 4-digit codes). Rendering templates
# across the size range that screenshots actually use lifted those to 99.6% and
# 99.5%. Do not collapse this back to one size.
RENDER_SIZES = (11, 14, 17, 21, 26, 32, 40, 52, 64)


def encode(values: list[float]) -> str:
    raw = bytes(max(0, min(255, int(round(v * 255)))) for v in values)
    return base64.b64encode(zlib.compress(raw, 9)).decode("ascii")


def find_fonts() -> list[Path]:
    import os

    candidates: list[Path] = []
    roots = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
        Path.home() / ".fonts",
        Path("/usr/share/fonts"),
        Path("/System/Library/Fonts"),
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for name in FONT_FILES:
            direct = root / name
            if direct.is_file():
                candidates.append(direct)
        # Some Linux layouts nest fonts in subdirectories.
        for name in FONT_FILES:
            for hit in root.rglob(name):
                if hit.is_file() and hit not in candidates:
                    candidates.append(hit)
    return candidates


def render_glyph(ch: str, font: ImageFont.FreeTypeFont, px: int) -> list[float] | None:
    """Render one character and normalise it to the template grid."""
    canvas = Image.new("L", (px * 3, px * 3), 255)
    draw = ImageDraw.Draw(canvas)
    try:
        draw.text((px, px), ch, font=font, fill=0)
    except Exception:
        return None

    bbox = canvas.point(lambda v: 255 - v).getbbox()  # ink bounding box
    if bbox is None:
        return None
    ink = canvas.crop(bbox)
    if ink.width < 2 or ink.height < 2:
        return None

    return normalize_glyph(ink)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args(argv)

    fonts = find_fonts()
    if not fonts:
        raise SystemExit("找不到任何可用字体，无法生成模板")

    charset = DIGITS + UPPER + LOWER + PUNCT
    glyphs: list[dict] = []
    used_fonts: list[str] = []
    seen: set[bytes] = set()

    for font_path in fonts:
        added = 0
        for px in RENDER_SIZES:
            try:
                font = ImageFont.truetype(str(font_path), px)
            except Exception:
                continue
            for ch in charset:
                values = render_glyph(ch, font, px)
                if values is None:
                    continue
                # Identical normalised bitmaps add nothing but size.
                key = bytes(max(0, min(255, int(round(v * 255)))) for v in values)
                if key in seen:
                    continue
                seen.add(key)
                glyphs.append(
                    {"ch": ch, "font": f"{font_path.name}@{px}", "z": encode(values)}
                )
                added += 1
        if added:
            used_fonts.append(f"{font_path.name}({added})")

    if not glyphs:
        raise SystemExit("没有渲染出任何字形")

    payload = {
        "template_version": TEMPLATE_VERSION,
        "height": CHAR_HEIGHT,
        "width": CHAR_WIDTH,
        "sizes": list(RENDER_SIZES),
        "charset": charset,
        "fonts": used_fonts,
        "count": len(glyphs),
        "glyphs": glyphs,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    print(f"[ocr_templates] {len(glyphs)} 个字形（去重后），来自 {len(used_fonts)} 个字体")
    print(f"[ocr_templates] 字号：{RENDER_SIZES}")
    print(f"[ocr_templates] -> {out_path.relative_to(PROJECT_ROOT)}"
          f"（{out_path.stat().st_size / 1024:.0f} KB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
