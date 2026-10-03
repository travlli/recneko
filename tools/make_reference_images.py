#!/usr/bin/env python3
"""Generate synthetic reference screens AND an augmented benchmark set.

WHY THIS FILE EXISTS, AND WHAT IT IS NOT
----------------------------------------
I have no real photos of Xiaomi/Redmi error screens in this environment (no
camera, no sample set), so this script draws stylised stand-ins. They let me

  * validate that the feature extraction / matching pipeline works end to end,
  * measure whether it is robust to the distortions a real phone photo has
    (scaling, perspective, JPEG artefacts, lighting, blur, noise),
  * pick sensible thresholds,

but they are **not** evidence of real-world accuracy. Drawing text as abstract
blocks keeps this honest: the recogniser is matching layout/colour/structure,
not reading characters, so a synthetic screen and a real one only agree if the
real screen happens to share that layout.

Real photos can be dropped into ``kb/image_refs/user/<label>/`` at any time and
will be combined with these by tools/build_references.py.

Usage
-----
    python tools/make_reference_images.py
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REF_ROOT = PROJECT_ROOT / "kb" / "image_refs"
REFERENCE_DIR = REF_ROOT / "synthetic"
BENCHMARK_DIR = REF_ROOT / "benchmark"

VARIATIONS_PER_CLASS = 3      # canonical reference images per class
BENCHMARK_PER_CANONICAL = 2   # augmented variants per canonical image

# --------------------------------------------------------------------------
# Screen definitions: (label, title, kb page, canvas, palette)
# --------------------------------------------------------------------------

PHONE = (1080, 2340)
DIALOG = (1024, 600)

SCREENS: list[dict] = [
    {
        "label": "recovery-menu",
        "title": "Recovery 主菜单（原厂 recovery 列表界面）",
        "kb_slug": "recovery-cant-load-android-system",
        "size": PHONE,
        "bg": (10, 10, 12),
        "fg": (232, 232, 232),
        "accent": (90, 190, 255),
        "style": "menu-list",
        "rows": 7,
    },
    {
        "label": "recovery-data-corrupt",
        "title": "Can't load Android system（数据损坏提示）",
        "kb_slug": "recovery-cant-load-android-system",
        "size": PHONE,
        "bg": (0, 0, 0),
        "fg": (245, 235, 200),
        "accent": (250, 200, 60),
        "style": "warning-block",
        "rows": 5,
    },
    {
        "label": "recovery-mount-failed",
        "title": "Recovery 挂载失败（failed to mount /data 红字刷屏）",
        "kb_slug": "recovery-cant-load-android-system",
        "size": PHONE,
        "bg": (8, 8, 10),
        "fg": (240, 80, 80),
        "accent": (240, 80, 80),
        "style": "console-lines",
        "rows": 14,
    },
    {
        "label": "fastboot-mode",
        "title": "Fastboot / Bootloader 界面（FASTBOOT 字样）",
        "kb_slug": "fastboot-devices-not-detected",
        "size": PHONE,
        "bg": (16, 16, 20),
        "fg": (255, 255, 255),
        "accent": (255, 140, 0),
        "style": "fastboot-logo",
        "rows": 2,
    },
    {
        "label": "edl-9008-mode",
        "title": "EDL / 9008 下载模式（黑屏小字）",
        "kb_slug": "qualcomm-edl-9008-enter",
        "size": PHONE,
        "bg": (0, 0, 0),
        "fg": (120, 160, 120),
        "accent": (120, 160, 120),
        "style": "console-lines",
        "rows": 10,
    },
    {
        "label": "spflash-error-dialog",
        "title": "SP Flash Tool 报错弹窗（BROM ERROR）",
        "kb_slug": "mtk-spflash-error-4032-4004-4008",
        "size": DIALOG,
        "bg": (240, 240, 240),
        "fg": (20, 20, 20),
        "accent": (200, 30, 30),
        "style": "tool-dialog",
        "rows": 4,
    },
    {
        "label": "miflash-error",
        "title": "MiFlash 刷机报错窗口",
        "kb_slug": "miflash-flash-script-errors",
        "size": DIALOG,
        "bg": (250, 250, 252),
        "fg": (30, 30, 30),
        "accent": (210, 60, 40),
        "style": "tool-dialog",
        "rows": 6,
    },
    {
        "label": "sideload-error",
        "title": "adb sideload 失败（PC 终端红字）",
        "kb_slug": "recovery-adb-sideload-errors",
        "size": DIALOG,
        "bg": (12, 12, 14),
        "fg": (230, 230, 230),
        "accent": (235, 70, 70),
        "style": "console-lines",
        "rows": 9,
    },
]


# --------------------------------------------------------------------------
# Drawing helpers. Text is drawn as blocks on purpose (see module docstring).
# --------------------------------------------------------------------------


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    color: tuple[int, int, int],
    rng: random.Random,
    gap: int = 6,
) -> None:
    """Draw a run of word-like blocks filling `width`."""
    cursor = x
    while cursor < x + width - height:
        word_width = rng.randint(int(height * 1.2), int(height * 4.0))
        if cursor + word_width > x + width:
            break
        draw.rounded_rectangle(
            (cursor, y, cursor + word_width, y + height), radius=max(2, height // 4), fill=color
        )
        cursor += word_width + gap


def draw_menu_list(
    draw: ImageDraw.ImageDraw,
    size: tuple[int, int],
    bg, fg, accent, rows: int, rng: random.Random
) -> None:
    width, height = size
    draw.rectangle((0, 0, width, height), fill=bg)
    # Header band
    draw.rectangle((0, 0, width, int(height * 0.12)), fill=(24, 24, 30))
    draw_text_block(draw, 60, int(height * 0.05), width - 120, 44, fg, rng)
    # Menu rows with selection highlight on one row
    selected = rng.randrange(rows)
    top = int(height * 0.18)
    row_height = int(height * 0.075)
    for index in range(rows):
        y = top + index * row_height
        if index == selected:
            draw.rectangle((40, y - 10, width - 40, y + row_height - 20), fill=(38, 62, 96))
            draw.rectangle((40, y - 10, 52, y + row_height - 20), fill=accent)
        draw_text_block(draw, 90, y, int(width * 0.62), 34, fg if index != selected else accent, rng)
    # Footer hint
    draw_text_block(draw, 60, height - 120, int(width * 0.5), 26, (140, 140, 150), rng)


def draw_warning_block(
    draw: ImageDraw.ImageDraw,
    size: tuple[int, int],
    bg, fg, accent, rows: int, rng: random.Random
) -> None:
    width, height = size
    draw.rectangle((0, 0, width, height), fill=bg)
    # Warning triangle-ish accent at top
    cx, cy, radius = width // 2, int(height * 0.28), int(width * 0.16)
    draw.polygon(
        [(cx, cy - radius), (cx + radius, cy + radius), (cx - radius, cy + radius)],
        fill=accent,
    )
    draw.polygon(
        [
            (cx, cy - radius + 34),
            (cx + radius - 44, cy + radius - 34),
            (cx - radius + 44, cy + radius - 34),
        ],
        fill=bg,
    )
    draw.rectangle((cx - 12, cy - 20, cx + 12, cy + 40), fill=accent)
    draw.ellipse((cx - 14, cy + 60, cx + 14, cy + 88), fill=accent)
    # Text block underneath
    y = int(height * 0.5)
    for _ in range(rows):
        draw_text_block(draw, 90, y, width - 180, 30, fg, rng)
        y += 62
    # Two buttons
    y = int(height * 0.78)
    for label_index in range(2):
        x = 120 + label_index * (width // 2)
        draw.rounded_rectangle(
            (x, y, x + int(width * 0.32), y + 66), radius=10,
            outline=accent, width=4, fill=(18, 18, 22),
        )
        draw_text_block(draw, x + 24, y + 18, int(width * 0.24), 28, accent, rng)


def draw_console_lines(
    draw: ImageDraw.ImageDraw,
    size: tuple[int, int],
    bg, fg, accent, rows: int, rng: random.Random
) -> None:
    width, height = size
    draw.rectangle((0, 0, width, height), fill=bg)
    # Title bar
    draw.rectangle((0, 0, width, 54), fill=(32, 32, 38))
    draw_text_block(draw, 16, 14, int(width * 0.34), 24, (200, 200, 210), rng)
    y = 80
    line_height = max(24, (height - 120) // max(rows, 1))
    for index in range(rows):
        # Most lines are ordinary, one or two are error-coloured
        is_error = index in (rng.randrange(rows), rng.randrange(rows))
        colour = accent if is_error else fg
        indent = 20 if index % 3 else 60
        draw_text_block(
            draw, indent, y, int(width * (0.5 + 0.4 * rng.random())) - indent,
            max(16, line_height - 12), colour, rng,
        )
        y += line_height


def draw_fastboot_logo(
    draw: ImageDraw.ImageDraw,
    size: tuple[int, int],
    bg, fg, accent, rows: int, rng: random.Random
) -> None:
    width, height = size
    draw.rectangle((0, 0, width, height), fill=bg)
    # Big centred wordmark (blocks, not glyphs)
    bar_width = int(width * 0.72)
    x = (width - bar_width) // 2
    draw_text_block(draw, x, int(height * 0.42), bar_width, 92, fg, rng, gap=18)
    # Accent rule underneath
    draw.rectangle(
        (x, int(height * 0.42) + 130, x + bar_width, int(height * 0.42) + 146), fill=accent
    )
    # Small status lines
    y = int(height * 0.55)
    for _ in range(rows + 2):
        draw_text_block(draw, x, y, int(bar_width * 0.6), 22, (150, 150, 160), rng)
        y += 48


def draw_tool_dialog(
    draw: ImageDraw.ImageDraw,
    size: tuple[int, int],
    bg, fg, accent, rows: int, rng: random.Random
) -> None:
    width, height = size
    draw.rectangle((0, 0, width, height), fill=(58, 58, 66))          # desktop backdrop
    margin_x, margin_y = int(width * 0.12), int(height * 0.14)
    draw.rounded_rectangle(
        (margin_x, margin_y, width - margin_x, height - margin_y), radius=8, fill=bg
    )
    # Title bar
    draw.rectangle(
        (margin_x, margin_y, width - margin_x, margin_y + 44), fill=(220, 220, 226)
    )
    draw_text_block(draw, margin_x + 16, margin_y + 12, int(width * 0.3), 20, (40, 40, 40), rng)
    # Error icon: red circle with a bar
    icon_x, icon_y = margin_x + 70, margin_y + 130
    draw.ellipse((icon_x - 34, icon_y - 34, icon_x + 34, icon_y + 34), fill=accent)
    draw.rectangle((icon_x - 26, icon_y - 6, icon_x + 26, icon_y + 6), fill=bg)
    # Message lines
    y = margin_y + 96
    for index in range(rows):
        colour = accent if index == 0 else fg
        draw_text_block(draw, icon_x + 70, y, int(width * 0.5), 26, colour, rng)
        y += 52
    # OK button
    button_w, button_h = 110, 40
    bx = width - margin_x - button_w - 24
    by = height - margin_y - button_h - 24
    draw.rounded_rectangle((bx, by, bx + button_w, by + button_h), radius=6,
                           outline=(150, 150, 158), width=2, fill=(238, 238, 242))
    draw_text_block(draw, bx + 30, by + 10, 50, 20, (50, 50, 50), rng)


STYLES = {
    "menu-list": draw_menu_list,
    "warning-block": draw_warning_block,
    "console-lines": draw_console_lines,
    "fastboot-logo": draw_fastboot_logo,
    "tool-dialog": draw_tool_dialog,
}


def render(spec: dict, seed: int) -> Image.Image:
    """Render one canonical screen."""
    rng = random.Random(seed)
    width, height = spec["size"]
    # Slight size jitter so references are not all pixel-identical.
    scale = 1.0 + rng.uniform(-0.12, 0.12)
    image = Image.new("RGB", (width, height), spec["bg"])
    draw = ImageDraw.Draw(image)
    drawer = STYLES[spec["style"]]
    drawer(draw, (width, height), spec["bg"], spec["fg"], spec["accent"], spec["rows"], rng)
    if abs(scale - 1.0) > 0.001:
        image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    return image


# --------------------------------------------------------------------------
# Augmentation: simulate a photo of a screen
# --------------------------------------------------------------------------


def _perspective(image: Image.Image, rng: random.Random, strength: float = 0.05) -> Image.Image:
    width, height = image.size
    dx, dy = width * strength, height * strength
    jitter = lambda: rng.uniform(-dx, dx)  # noqa: E731
    jitter_y = lambda: rng.uniform(-dy, dy)  # noqa: E731
    # PIL transform: destination -> source coefficients (8-tuple).
    return image.transform(
        (width, height),
        Image.PERSPECTIVE,
        (
            1 + rng.uniform(-strength, strength), jitter(),
            jitter(),
            jitter_y(),
            1 + rng.uniform(-strength, strength),
            jitter_y(),
            jitter() / max(width, 1) * 0.001,
            jitter_y() / max(height, 1) * 0.001,
        ),
        Image.BICUBIC,
    )


def augment(image: Image.Image, seed: int) -> Image.Image:
    """Apply realistic photo distortions (scale, rotate, light, blur, noise)."""
    rng = random.Random(seed)
    result = image

    # Random re-scale (photo resolution differs from screen resolution)
    factor = rng.uniform(0.4, 0.9)
    result = result.resize(
        (max(8, int(result.width * factor)), max(8, int(result.height * factor))),
        Image.LANCZOS,
    )

    if rng.random() < 0.5:
        result = _perspective(result, rng, strength=rng.uniform(0.02, 0.06))

    if rng.random() < 0.6:
        result = result.rotate(
            rng.uniform(-4, 4), resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0)
        )

    # Lighting: brightness / contrast / colour cast
    from PIL import ImageEnhance

    result = ImageEnhance.Brightness(result).enhance(rng.uniform(0.55, 1.45))
    result = ImageEnhance.Contrast(result).enhance(rng.uniform(0.7, 1.3))
    if rng.random() < 0.4:
        tint = Image.new("RGB", result.size, (
            rng.randint(200, 255), rng.randint(200, 255), rng.randint(200, 255)
        ))
        result = Image.blend(result, tint, rng.uniform(0.03, 0.12))

    # Camera shake / focus blur
    if rng.random() < 0.5:
        result = result.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 1.6)))

    # Sensor noise
    if rng.random() < 0.6:
        noise = Image.effect_noise(result.size, rng.uniform(6, 20)).convert("L")
        result = Image.blend(result, Image.merge("RGB", (noise, noise, noise)), 0.06)

    # JPEG round trip
    if rng.random() < 0.8:
        import io

        buffer = io.BytesIO()
        result.save(buffer, format="JPEG", quality=rng.randint(45, 88))
        buffer.seek(0)
        result = Image.open(buffer).convert("RGB")

    return result


# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--clean", action="store_true", help="先清空已生成的图")
    args = parser.parse_args(argv)

    if args.clean:
        import shutil

        for directory in (REFERENCE_DIR, BENCHMARK_DIR):
            if directory.is_dir():
                shutil.rmtree(directory)

    total_refs = 0
    total_bench = 0

    for spec in SCREENS:
        label = spec["label"]
        ref_dir = REFERENCE_DIR / label
        bench_dir = BENCHMARK_DIR / label
        ref_dir.mkdir(parents=True, exist_ok=True)
        bench_dir.mkdir(parents=True, exist_ok=True)

        for index in range(VARIATIONS_PER_CLASS):
            seed = hash((label, index)) & 0xFFFF
            canonical = render(spec, seed)
            canonical_path = ref_dir / f"{label}-{index}.png"
            canonical.save(canonical_path, format="PNG")
            total_refs += 1

            for variant in range(BENCHMARK_PER_CANONICAL):
                aug_seed = hash((label, index, variant, "aug")) & 0xFFFF
                augmented = augment(canonical, aug_seed)
                augmented.save(
                    bench_dir / f"{label}-{index}-aug{variant}.jpg",
                    format="JPEG",
                    quality=80,
                )
                total_bench += 1

    print(f"[make_refs] 参考图 {total_refs} 张 -> {REFERENCE_DIR}")
    print(f"[make_refs] 基准图 {total_bench} 张 -> {BENCHMARK_DIR}")
    print(f"[make_refs] 类别：{', '.join(s['label'] for s in SCREENS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
