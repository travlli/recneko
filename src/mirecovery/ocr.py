"""Text recognition (OCR) for screenshots, with pluggable backends.

Why this exists
---------------
Screen-*type* recognition (``recognize.py``) can tell a recovery menu from a
fastboot screen, but it cannot read the text - so it cannot distinguish
``ERROR 4032`` from ``ERROR 4004``. Extracting the text and feeding it into the
existing text pipeline is far more precise than matching pixels.

Backends
--------
Tried in order, best first; the first available one wins:

1. **Tesseract** (``pytesseract`` + the ``tesseract`` binary) - best quality,
   including Chinese. Desktop only: it is a C++ program and cannot ship in the
   apk.
2. **RapidOCR** (``rapidocr_onnxruntime``) - good quality, also desktop only
   (Chaquopy has no onnxruntime).
3. **Built-in template matcher** - pure Pillow, always available, works in the
   apk. It matches segmented glyphs against bitmaps rendered at build time by
   ``tools/build_ocr_templates.py``.

Honest scope of the built-in backend
------------------------------------
* **Latin + digits only.** CJK would need thousands of templates; Chinese UI
  text is not recognised by it (Tesseract/RapidOCR handle it if installed).
* It is a *template* matcher, so it is strongest on clean, flat, high-contrast
  screenshots (phone screenshots, tool dialogs) and weak on photographs -
  perspective, blur, and unknown fonts degrade it quickly. ``confidence`` is
  reported so callers can refuse low-quality results instead of inventing text.
* It cannot invent characters it has no template for; unknown glyphs become
  ``?`` and drag the confidence down.
"""

from __future__ import annotations

import base64
import math
import re
import shutil
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageFilter

# Template grid. Keep in sync with tools/build_ocr_templates.py.
CHAR_HEIGHT = 24
CHAR_WIDTH = 16
TEMPLATE_VERSION = 1

# A glyph match below this is treated as "not recognised".
MIN_GLYPH_SCORE = 0.55
# Lines with fewer foreground pixels than this are treated as noise.
MIN_LINE_INK = 6
# Text smaller than this many pixels tall is upscaled before segmentation.
TARGET_LINE_HEIGHT = 28
MAX_UPSCALE = 6

TEMPLATES_PATH = Path(__file__).resolve().parent / "data" / "ocr_templates.json"

# Characters worth keeping when cleaning up recognised text.
_KEEP_RE = re.compile(r"[^0-9A-Za-z:./\\\-_()\[\]<>,;'\"=+*#%!?@&|~^$ ]+")


# --------------------------------------------------------------------------
# Result types
# --------------------------------------------------------------------------


@dataclass
class OcrLine:
    """One recognised line of text."""

    text: str
    confidence: float
    y: int = 0
    height: int = 0


@dataclass
class OcrResult:
    """Outcome of reading text from an image."""

    text: str = ""
    confidence: float = 0.0
    backend: str = ""
    lines: list[OcrLine] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.text.strip())

    def __bool__(self) -> bool:  # allows `if result:`
        return self.ok


# --------------------------------------------------------------------------
# Glyph normalisation (shared with the template builder)
# --------------------------------------------------------------------------


def _pixels(image: Image.Image) -> list:
    """Pixel values, using the non-deprecated Pillow API when available.

    ``Image.getdata`` is deprecated in Pillow 12 and removed in Pillow 14.
    """
    getter = getattr(image, "get_flattened_data", None)
    if getter is not None:
        return list(getter())
    return list(image.getdata())  # pragma: no cover - older Pillow only


def normalize_glyph(ink: Image.Image) -> list[float]:
    """Scale a cropped glyph to the template grid, preserving aspect ratio.

    Aspect ratio is preserved and the result is centred, because squashing a
    narrow ``1`` to fill the grid makes it look like ``l`` or ``I``.
    """
    target_w, target_h = CHAR_WIDTH, CHAR_HEIGHT
    grey = ink.convert("L")
    scale = min(target_w / grey.width, target_h / grey.height)
    new_w = max(1, int(round(grey.width * scale)))
    new_h = max(1, int(round(grey.height * scale)))
    resized = grey.resize((new_w, new_h), Image.LANCZOS)

    plate = Image.new("L", (target_w, target_h), 255)
    plate.paste(resized, ((target_w - new_w) // 2, (target_h - new_h) // 2))

    # Invert so ink is high, then normalise to 0..1.
    return [1.0 - (v / 255.0) for v in _pixels(plate)]


def encode_glyph(values: list[float]) -> str:
    raw = bytes(max(0, min(255, int(round(v * 255)))) for v in values)
    return base64.b64encode(zlib.compress(raw, 9)).decode("ascii")


def decode_glyph(blob: str) -> list[float]:
    raw = zlib.decompress(base64.b64decode(blob.encode("ascii")))
    return [b / 255.0 for b in raw]


def _zncc(a: list[float], b: list[float]) -> float:
    """Zero-normalised cross-correlation, mapped to [0, 1]."""
    if len(a) != len(b) or not a:
        return 0.0
    n = len(a)
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    va = [x - mean_a for x in a]
    vb = [x - mean_b for x in b]
    denom = math.sqrt(sum(x * x for x in va)) * math.sqrt(sum(y * y for y in vb))
    if denom < 1e-9:
        return 0.0
    corr = sum(x * y for x, y in zip(va, vb)) / denom
    return (max(-1.0, min(1.0, corr)) + 1.0) / 2.0


# --------------------------------------------------------------------------
# Template library
# --------------------------------------------------------------------------


class TemplateSet:
    """Bundled glyph templates, indexed by character.

    Matching is two-stage for speed. With 1274 templates, running full ZNCC over
    every one for every glyph took minutes per screenshot; instead each template
    is reduced to a coarse profile + ink mass, candidates are shortlisted on
    those (cheap arithmetic), and ZNCC runs only on the shortlist.
    """

    # Coarse grid used for the cheap prefilter.
    PROFILE_W = 4
    PROFILE_H = 6
    # How many candidates get the exact comparison.
    SHORTLIST = 24

    def __init__(self, glyphs: dict[str, list[list[float]]], fonts: list[str] | None = None):
        self.glyphs = glyphs
        self.fonts = fonts or []
        self._index: list[tuple[str, list[float], list[float], float]] = []
        self._np = None
        try:  # numpy makes the exact stage ~5x faster; optional by design
            import numpy as np

            self._np = np
        except Exception:
            self._np = None
        self._build_index()

    def _profile(self, values: list[float]) -> list[float]:
        """Downsample a glyph to a small grid of average intensities."""
        out: list[float] = []
        for gy in range(self.PROFILE_H):
            y0 = gy * CHAR_HEIGHT // self.PROFILE_H
            y1 = max(y0 + 1, (gy + 1) * CHAR_HEIGHT // self.PROFILE_H)
            for gx in range(self.PROFILE_W):
                x0 = gx * CHAR_WIDTH // self.PROFILE_W
                x1 = max(x0 + 1, (gx + 1) * CHAR_WIDTH // self.PROFILE_W)
                total = 0.0
                count = 0
                for y in range(y0, y1):
                    base = y * CHAR_WIDTH
                    for x in range(x0, x1):
                        total += values[base + x]
                        count += 1
                out.append(total / max(1, count))
        return out

    def _build_index(self) -> None:
        for ch, variants in self.glyphs.items():
            for values in variants:
                profile = self._profile(values)
                self._index.append((ch, values, profile, sum(values)))

    @property
    def charset(self) -> str:
        return "".join(sorted(self.glyphs))

    @classmethod
    def load(cls, path: Path | None = None) -> "TemplateSet":
        path = Path(path) if path else TEMPLATES_PATH
        if not path.is_file():
            raise FileNotFoundError(
                f"找不到 OCR 字形模板：{path}\n"
                "请运行：python tools/build_ocr_templates.py"
            )
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("template_version") != TEMPLATE_VERSION:
            raise ValueError(
                f"OCR 模板版本不匹配（模板={payload.get('template_version')}，"
                f"程序={TEMPLATE_VERSION}）；请重新运行 tools/build_ocr_templates.py"
            )
        glyphs: dict[str, list[list[float]]] = {}
        for item in payload.get("glyphs", []):
            values = decode_glyph(item["z"])
            glyphs.setdefault(str(item["ch"]), []).append(values)
        return cls(glyphs, list(payload.get("fonts") or []))

    def match(self, values: list[float], charset: str | None = None) -> tuple[str, float]:
        """Best-matching character and its score.

        Stage 1 shortlists by coarse-profile distance; stage 2 scores the
        shortlist with full ZNCC. Without the shortlist this is ~1274 full
        correlations per glyph, which is far too slow to be usable.
        """
        if not self._index:
            return "", 0.0

        query_profile = self._profile(values)
        query_ink = sum(values)

        scored: list[tuple[float, int]] = []
        for position, (ch, _t_values, profile, ink) in enumerate(self._index):
            if charset is not None and ch not in charset:
                continue
            # Ink mass and coarse shape are enough to reject most templates.
            rough = abs(ink - query_ink) * 0.5 + sum(
                abs(a - b) for a, b in zip(query_profile, profile)
            )
            scored.append((rough, position))

        if not scored:
            return "", 0.0

        scored.sort(key=lambda item: item[0])
        shortlist = scored[: self.SHORTLIST]

        best_ch, best_score = "", 0.0
        if self._np is not None:
            np = self._np
            query = np.asarray(values, dtype=np.float32)
            query = query - query.mean()
            q_norm = float(np.sqrt((query * query).sum()))
            if q_norm < 1e-9:
                return "", 0.0
            query = query / q_norm
            for _rough, position in shortlist:
                ch, t_values, _profile, _ink = self._index[position]
                template = np.asarray(t_values, dtype=np.float32)
                template = template - template.mean()
                t_norm = float(np.sqrt((template * template).sum()))
                if t_norm < 1e-9:
                    continue
                corr = float(np.dot(query, template / t_norm))
                score = (max(-1.0, min(1.0, corr)) + 1.0) / 2.0
                if score > best_score:
                    best_ch, best_score = ch, score
        else:
            for _rough, position in shortlist:
                ch, t_values, _profile, _ink = self._index[position]
                score = _zncc(values, t_values)
                if score > best_score:
                    best_ch, best_score = ch, score

        return best_ch, best_score


# --------------------------------------------------------------------------
# Image preprocessing
# --------------------------------------------------------------------------


def _otsu_threshold(histogram: list[int], total: int) -> int:
    """Otsu's method: pick the threshold that best separates two classes."""
    sum_all = sum(i * h for i, h in enumerate(histogram))
    sum_bg = 0.0
    weight_bg = 0
    best_variance = -1.0
    best_threshold = 127
    for threshold in range(256):
        weight_bg += histogram[threshold]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += threshold * histogram[threshold]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = threshold
    return best_threshold


def binarize(image: Image.Image) -> Image.Image:
    """Return a mode-'1'-like L image where text is dark (0) on light (255).

    Screens come in both polarities (light text on a dark recovery menu, dark
    text on a light tool dialog), so the polarity is detected rather than
    assumed: whichever class covers fewer pixels is treated as the text.
    """
    grey = image.convert("L")
    histogram = grey.histogram()
    total = sum(histogram)
    threshold = _otsu_threshold(histogram, total)
    binary = grey.point(lambda v: 0 if v <= threshold else 255, mode="L")

    dark = sum(histogram[: threshold + 1])
    if dark > total * 0.5:
        # Dark pixels dominate -> it was light text on dark, so invert.
        binary = binary.point(lambda v: 255 - v, mode="L")
    return binary


def _upscale_for_text(binary: Image.Image) -> Image.Image:
    """Enlarge small text so segmentation has enough pixels to work with."""
    # Estimate stroke/line height from the ink bounding box of each row band.
    ink_rows = []
    pixels = binary.load()
    width, height = binary.size
    for y in range(height):
        row_ink = sum(1 for x in range(width) if pixels[x, y] < 128)
        ink_rows.append(row_ink)

    # Rough line height: count runs of ink rows.
    runs = 0
    in_run = False
    run_lengths = []
    current = 0
    for value in ink_rows:
        if value > 0:
            if not in_run:
                in_run = True
                current = 0
            current += 1
        else:
            if in_run:
                in_run = False
                run_lengths.append(current)
    if in_run:
        run_lengths.append(current)

    if not run_lengths:
        return binary
    typical = sorted(run_lengths)[len(run_lengths) // 2]
    if typical <= 0 or typical >= TARGET_LINE_HEIGHT:
        return binary
    factor = min(MAX_UPSCALE, max(1, int(round(TARGET_LINE_HEIGHT / typical))))
    if factor <= 1:
        return binary
    return binary.resize((width * factor, height * factor), Image.LANCZOS)


# --------------------------------------------------------------------------
# Built-in backend
# --------------------------------------------------------------------------


class BuiltinOcrBackend:
    """Template-matching OCR using only Pillow."""

    name = "builtin"

    def __init__(self, templates: TemplateSet | None = None, charset: str | None = None):
        self.templates = templates if templates is not None else TemplateSet.load()
        self.charset = charset

    @staticmethod
    def available() -> bool:
        return TEMPLATES_PATH.is_file()

    def read(self, image: Image.Image) -> OcrResult:
        binary = _upscale_for_text(binarize(image))
        lines = self._segment_lines(binary)
        if not lines:
            return OcrResult(backend=self.name, error="未检测到文字")

        out_lines: list[OcrLine] = []
        for y0, y1, band in lines:
            text, confidence = self._read_line(band)
            if text.strip():
                out_lines.append(
                    OcrLine(text=text, confidence=confidence, y=y0, height=y1 - y0)
                )

        if not out_lines:
            return OcrResult(backend=self.name, error="未能识别出字符")

        text = "\n".join(line.text for line in out_lines)
        weights = [len(line.text) for line in out_lines]
        confidence = sum(
            line.confidence * weight for line, weight in zip(out_lines, weights)
        ) / max(1, sum(weights))
        return OcrResult(
            text=text, confidence=round(confidence, 4), backend=self.name, lines=out_lines
        )

    # -- segmentation --------------------------------------------------

    @staticmethod
    def _segment_lines(binary: Image.Image) -> list[tuple[int, int, Image.Image]]:
        """Split the image into horizontal text bands."""
        width, height = binary.size
        pixels = binary.load()
        row_ink = [
            sum(1 for x in range(width) if pixels[x, y] < 128) for y in range(height)
        ]
        bands: list[tuple[int, int, Image.Image]] = []
        start: int | None = None
        for y, ink in enumerate(row_ink + [0]):
            if ink > 0 and start is None:
                start = y
            elif ink == 0 and start is not None:
                if y - start >= 3:
                    band = binary.crop((0, start, width, y))
                    if sum(row_ink[start:y]) >= MIN_LINE_INK:
                        bands.append((start, y, band))
                start = None
        return bands

    def _read_line(self, band: Image.Image) -> tuple[str, float]:
        """Segment a line into glyphs and classify each one."""
        width, height = band.size
        pixels = band.load()
        col_ink = [
            sum(1 for y in range(height) if pixels[x, y] < 128) for x in range(width)
        ]

        # Split into ink runs, remembering the gap width before each run.
        segments: list[tuple[int, int, int]] = []  # (x0, x1, gap_before)
        start: int | None = None
        gap = 0
        for x, ink in enumerate(col_ink + [0]):
            if ink > 0:
                if start is None:
                    start = x
                    gap_before = gap
                    gap = 0
            else:
                if start is not None:
                    segments.append((start, x, gap_before))
                    start = None
                gap += 1
        if not segments:
            return "", 0.0

        # A gap wider than this fraction of the typical glyph width is a space.
        widths = [x1 - x0 for x0, x1, _ in segments]
        typical = sorted(widths)[len(widths) // 2] if widths else 1
        space_gap = max(typical * 0.6, 3)

        chars: list[str] = []
        scores: list[float] = []
        for x0, x1, gap_before in segments:
            if gap_before >= space_gap and chars:
                chars.append(" ")
            ink = band.crop((x0, 0, x1, height))
            values = normalize_glyph(ink)
            ch, score = self.templates.match(values, self.charset)
            if score < MIN_GLYPH_SCORE or not ch:
                chars.append("?")
                scores.append(score)
            else:
                chars.append(ch)
                scores.append(score)

        text = "".join(chars)
        confidence = sum(scores) / len(scores) if scores else 0.0
        return text, confidence


# --------------------------------------------------------------------------
# Optional high-quality backends
# --------------------------------------------------------------------------


class TesseractBackend:
    """Tesseract via pytesseract. Requires the tesseract binary on PATH."""

    name = "tesseract"

    @staticmethod
    def available() -> bool:
        if shutil.which("tesseract") is None:
            return False
        try:
            import pytesseract  # noqa: F401

            return True
        except Exception:
            return False

    def read(self, image: Image.Image) -> OcrResult:
        import pytesseract

        try:
            text = pytesseract.image_to_string(image, config="--psm 6")
        except Exception as exc:
            return OcrResult(backend=self.name, error=f"{type(exc).__name__}: {exc}")
        lines = [OcrLine(text=line.strip(), confidence=1.0) for line in text.splitlines()]
        lines = [line for line in lines if line.text]
        return OcrResult(
            text="\n".join(line.text for line in lines),
            confidence=1.0 if lines else 0.0,
            backend=self.name,
            lines=lines,
        )


class RapidOcrBackend:
    """RapidOCR (onnxruntime). Optional; cannot ship in the Android build."""

    name = "rapidocr"

    def __init__(self) -> None:
        from rapidocr_onnxruntime import RapidOCR

        self._engine = RapidOCR()

    @staticmethod
    def available() -> bool:
        try:
            import rapidocr_onnxruntime  # noqa: F401

            return True
        except Exception:
            return False

    def read(self, image: Image.Image) -> OcrResult:
        import numpy as np

        try:
            result, _ = self._engine(np.array(image.convert("RGB")))
        except Exception as exc:
            return OcrResult(backend=self.name, error=f"{type(exc).__name__}: {exc}")
        if not result:
            return OcrResult(backend=self.name, error="未检测到文字")
        lines = [
            OcrLine(text=str(item[1]).strip(), confidence=float(item[2]))
            for item in result
            if len(item) >= 3
        ]
        lines = [line for line in lines if line.text]
        confidence = sum(line.confidence for line in lines) / len(lines) if lines else 0.0
        return OcrResult(
            text="\n".join(line.text for line in lines),
            confidence=round(confidence, 4),
            backend=self.name,
            lines=lines,
        )


class WindowsOcrBackend:
    """Windows' built-in OCR engine, via the ``winsdk`` bindings.

    The best backend on Windows: it ships with the OS (no external binary,
    nothing to install), runs offline, and is the same engine PowerToys Text
    Extractor uses. Measured on rendered log lines it reads long strings
    exactly; its misses are the usual ``1``/``l`` and ``0``/``O`` confusions,
    which ``normalize_confusions`` cleans up for keyword search.

    Two behaviours worth knowing:

    * It needs reasonably large text. Small images return *nothing at all*
      (measured: 28/48 empty at 1x, 0/48 after 3x upscaling), so images are
      upscaled before being handed over.
    * Language support depends on installed OCR language packs. Chinese returned
      empty on this machine even though the engine reports ``zh-Hans-CN``; treat
      CJK as unavailable unless verified locally.
    """

    name = "windows"

    # Windows OCR misses small text entirely; scale up until the short side is
    # at least this many pixels.
    MIN_SIDE = 480
    MAX_UPSCALE = 6

    @staticmethod
    def available() -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winsdk.windows.media.ocr  # noqa: F401

            return True
        except Exception:
            return False

    def __init__(self, language: str | None = None) -> None:
        from winsdk.windows.globalization import Language
        from winsdk.windows.media.ocr import OcrEngine

        self._engine = None
        self._loop = None
        if language:
            try:
                self._engine = OcrEngine.try_create_from_language(Language(language))
            except Exception:
                self._engine = None
        if self._engine is None:
            self._engine = OcrEngine.try_create_from_user_profile_languages()
        if self._engine is None:
            raise RuntimeError("Windows OCR 引擎不可用（未安装任何 OCR 语言包）")

    def _run(self, coro):
        """Run a coroutine, reusing one event loop.

        ``asyncio.run`` creates and tears down a fresh Proactor loop on every
        call. Doing that repeatedly alongside Tk's COM initialisation made the
        process crash with an access violation at interpreter shutdown (seen
        flakily when running the full test suite). One persistent loop avoids it.
        """
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass  # no loop running: the normal path
        else:  # already inside a loop (e.g. a notebook): use a helper thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: self._run(coro)).result()

        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop.run_until_complete(coro)

    def _to_bitmap(self, image: Image.Image):
        from winsdk.windows.graphics.imaging import (
            BitmapAlphaMode,
            BitmapPixelFormat,
            SoftwareBitmap,
        )
        from winsdk.windows.security.cryptography import CryptographicBuffer

        rgba = image.convert("RGBA")
        width, height = rgba.size
        red, green, blue, alpha = rgba.split()
        # Windows expects BGRA8.
        bgra = Image.merge("RGBA", (blue, green, red, alpha))
        buffer = CryptographicBuffer.create_from_byte_array(bgra.tobytes())
        return SoftwareBitmap.create_copy_from_buffer(
            buffer, BitmapPixelFormat.BGRA8, width, height, BitmapAlphaMode.PREMULTIPLIED
        )

    def _prepare(self, image: Image.Image) -> Image.Image:
        rgb = image.convert("RGB")
        short_side = min(rgb.size)
        if short_side and short_side < self.MIN_SIDE:
            factor = min(self.MAX_UPSCALE, max(1, int(self.MIN_SIDE / short_side) + 1))
            rgb = rgb.resize((rgb.width * factor, rgb.height * factor), Image.LANCZOS)
        return rgb

    def read(self, image: Image.Image) -> OcrResult:
        async def run() -> str:
            bitmap = self._to_bitmap(self._prepare(image))
            result = await self._engine.recognize_async(bitmap)
            return result.text or ""

        try:
            text = self._run(run())
        except Exception as exc:
            return OcrResult(backend=self.name, error=f"{type(exc).__name__}: {exc}")

        lines = [
            OcrLine(text=line.strip(), confidence=1.0)
            for line in text.splitlines()
            if line.strip()
        ]
        return OcrResult(
            text="\n".join(line.text for line in lines),
            confidence=1.0 if lines else 0.0,
            backend=self.name,
            lines=lines,
            error="" if lines else "未检测到文字",
        )


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

_BACKEND_CACHE: dict[str, object] = {}


def available_backends() -> list[str]:
    """Names of usable backends, best first."""
    names: list[str] = []
    if WindowsOcrBackend.available():
        names.append(WindowsOcrBackend.name)
    if TesseractBackend.available():
        names.append(TesseractBackend.name)
    if RapidOcrBackend.available():
        names.append(RapidOcrBackend.name)
    if BuiltinOcrBackend.available():
        names.append(BuiltinOcrBackend.name)
    return names


def _get_backend(name: str, charset: str | None):
    key = f"{name}:{charset or ''}"
    if key not in _BACKEND_CACHE:
        if name == WindowsOcrBackend.name:
            _BACKEND_CACHE[key] = WindowsOcrBackend()
        elif name == TesseractBackend.name:
            _BACKEND_CACHE[key] = TesseractBackend()
        elif name == RapidOcrBackend.name:
            _BACKEND_CACHE[key] = RapidOcrBackend()
        else:
            _BACKEND_CACHE[key] = BuiltinOcrBackend(charset=charset)
    return _BACKEND_CACHE[key]


def recognize_text(
    image: Image.Image,
    backend: str | None = None,
    charset: str | None = None,
    min_confidence: float = 0.0,
) -> OcrResult:
    """Read text from an image.

    ``backend`` forces a specific engine; by default the best available one is
    used. ``charset`` restricts the built-in matcher (e.g. digits only for error
    codes). Results below ``min_confidence`` are returned with empty ``text`` so
    callers do not act on noise.
    """
    try:
        names = [backend] if backend else available_backends()
    except Exception as exc:
        return OcrResult(error=f"{type(exc).__name__}: {exc}")

    if not names:
        return OcrResult(
            error="没有可用的 OCR 后端。内置后端需要先运行 "
                  "tools/build_ocr_templates.py 生成字形模板。"
        )

    last_error = ""
    for name in names:
        try:
            engine = _get_backend(name, charset)
        except Exception as exc:
            last_error = f"{name}: {type(exc).__name__}: {exc}"
            continue
        try:
            result = engine.read(image)
        except Exception as exc:
            last_error = f"{name}: {type(exc).__name__}: {exc}"
            continue

        if result.ok and result.confidence >= min_confidence:
            return result
        if result.ok:
            # Recognised something, but not confidently enough to report.
            return OcrResult(
                backend=result.backend,
                confidence=result.confidence,
                lines=result.lines,
                error=f"文字识别置信度过低（{result.confidence:.0%} < "
                      f"{min_confidence:.0%}）",
            )
        last_error = result.error or last_error

    return OcrResult(backend=names[-1] if names else "", error=last_error or "识别失败")


def clean_text(text: str) -> str:
    """Drop characters the matcher could not identify, keeping useful ones.

    ``?`` is the built-in backend's "unknown glyph" marker; leaving them in
    would pollute keyword search with noise.
    """
    return _KEEP_RE.sub(" ", text.replace("?", " ")).strip()


# --------------------------------------------------------------------------
# Error-code oriented helpers
# --------------------------------------------------------------------------

_CODE_RE = re.compile(r"\b(?:ERROR|ERR)?[\s:_-]*([1-5]\d{3})\b", re.IGNORECASE)


def extract_error_codes(text: str) -> list[str]:
    """Pull SP Flash Tool style numeric codes out of recognised text.

    The built-in matcher is weakest on mixed-case prose and strongest on
    digits, so a digits-only pass is a cheap, high-value second attempt when the
    general pass finds nothing.
    """
    found: list[str] = []
    for match in _CODE_RE.finditer(text):
        code = match.group(1)
        if code not in found:
            found.append(code)
    return found


def recognize_digits(image: Image.Image, backend: str | None = None) -> OcrResult:
    """Read an image restricted to digits (for error-code plates)."""
    return recognize_text(
        image, backend=backend, charset="0123456789", min_confidence=0.0
    )


# --------------------------------------------------------------------------
# Post-processing
# --------------------------------------------------------------------------

# OCR's classic look-alike substitutions. Measured on Windows OCR output:
# "failed" -> "fai1ed", "allowed" -> "a110wed", "Invalid" -> "lnvalid".
# Left alone these break keyword search.
#
# Applied per token and never to an all-digit token: an error code must stay
# exact, and "1" inside "4032"-style codes is far more likely a real 1 than a
# misread "l".
_CONFUSIONS = {
    "0": "o", "1": "l", "5": "s", "8": "b", "2": "z", "6": "g",
    "|": "l", "!": "l", "$": "s",
}

_TOKEN_SPLIT = re.compile(r"([0-9A-Za-z|!$]+)")


def normalize_confusions(text: str) -> str:
    """Fold OCR look-alikes so keyword matching survives them.

    All-digit tokens are left untouched so error codes are not corrupted.
    """
    if not text:
        return ""
    out: list[str] = []
    for chunk in _TOKEN_SPLIT.split(text):
        if not chunk:
            continue
        if chunk.isdigit():
            out.append(chunk)
        else:
            out.append("".join(_CONFUSIONS.get(ch, ch) for ch in chunk))
    return "".join(out)


def keywords_from_text(text: str, min_length: int = 4) -> list[str]:
    """Pull searchable words out of OCR output, confusion-normalised.

    Feeds the existing knowledge-base search, which is far more precise than
    pixel matching - that is the whole point of doing OCR at all.
    """
    normalised = normalize_confusions(clean_text(text))
    words: list[str] = []
    for token in re.split(r"[^0-9A-Za-z]+", normalised):
        token = token.strip()
        if len(token) < min_length:
            continue
        if token not in words:
            words.append(token)
    return words


# --------------------------------------------------------------------------
# "Is this actually an error?" gate
# --------------------------------------------------------------------------

# Words that indicate the screen is reporting a failure. Deliberately broad, but
# note they must appear as *error* language - a plain UI label is not one.
_ERROR_INDICATORS = (
    "error", "fail", "failed", "failure", "fatal", "invalid", "unable",
    "cannot", "can't", "couldn't", "corrupt", "corruption", "denied", "abort",
    "aborted", "refused", "rejected", "mismatch", "timeout", "timed out",
    "not allowed", "not found", "no such", "unknown command", "unsupported",
    "verification failed", "signature", "checksum", "bad ", "broken",
    "cannot load", "can't load", "unable to mount", "failed to mount",
    "stack", "panic", "brick", "restart", "stuck", "loop",
)

# Chinese equivalents, for screenshots of Chinese UIs.
_ERROR_INDICATORS_CN = (
    "错误", "失败", "无法", "不能", "校验", "损坏", "异常", "中断", "超时",
    "拒绝", "不匹配", "不支持", "找不到", "未找到", "重启", "卡住", "变砖",
    "刷机失败", "开不了机", "打不开",
)

_CODE_RE_FOR_ERROR = re.compile(r"\b[1-5]\d{3}\b")


def looks_like_error(text: str) -> tuple[bool, list[str]]:
    """Does this text report a failure?

    Returns ``(is_error, matched_indicators)``.

    This gate exists because real screenshots of *normal* screens were being
    handed confident repair instructions. Measured on real downloaded images: a
    plain fastboot screen (device info only) matched a KB page at score 72.7, and
    an update-progress screen matched at 16.6 - neither contained any error at
    all. Presenting a flashing procedure for a screen that shows no fault is the
    worst failure mode this app can have, so text alone is not enough evidence.
    """
    if not text:
        return False, []
    lowered = text.lower()
    hits = [word for word in _ERROR_INDICATORS if word in lowered]
    hits += [word for word in _ERROR_INDICATORS_CN if word in text]
    codes = _CODE_RE_FOR_ERROR.findall(text)
    if codes:
        hits.extend(f"错误码 {code}" for code in codes)
    return bool(hits), hits
