"""Image features for screen recognition.

The recogniser must work on **both** the Windows exe and the Android apk, so it
uses only Pillow plus (optionally) numpy — the two imaging dependencies that
are actually available in BeeWare's Android (Chaquopy) package set. There is no
Tesseract binary and no onnxruntime available there, which rules out OCR
libraries; recognising the *screen* is what remains feasible everywhere.

What is extracted
-----------------
* **dHash / aHash** (64 bit each, pure Python — no imagehash dependency):
   robust to scaling and compression, good at "same screen" matching.
* **Zero-normalised cross-correlation (ZNCC) thumbnails** — a 64x64 greyscale
  thumbnail plus the same for each RGB channel, stored with their mean and
  standard deviation. ZNCC is invariant to brightness and contrast changes and,
  crucially, ignores flat background: a mean-absolute-difference metric on a
  screen that is 80% black just measures "both are black", which made every
  dark screenshot look ~0.9 similar to every other one.
* **Edge-magnitude thumbnail** — ZNCC over edges emphasises where the text and
  UI elements are, ignoring whether the user inverted colours.
* **RGB and hue histograms** — palette, separates a blue dialog from a black
  console.
* **Grid brightness** (4x4) — coarse layout, kept for explainability.
* **Edge density / brightness / contrast** — global statistics.

Everything is stored as a small JSON document so reference sets can be built
once and shipped, and so users can add their own photos without retraining.
"""

from __future__ import annotations

import base64
import json
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageFilter

# Canonical working size for all feature extraction.
HASH_SIZE = 8          # -> 8x8 = 64 bit hash
HIST_SIZE = (128, 128)  # small thumbnail is enough for colour statistics
THUMB_SIZE = (64, 64)   # thumbnail used for ZNCC matching
# Measured on the synthetic distortion benchmark: 96x96 gave identical
# precision/coverage to 64x64 while tripling the data shipped, so 64 wins.
GRID = 4               # 4x4 brightness grid
RGB_BINS = 16
RGB_CHANNELS = 3       # rgb_hist is three concatenated channel histograms
HUE_BINS = 12

FEATURE_VERSION = 2


# --------------------------------------------------------------------------
# Pure-Python / Pillow primitives
# --------------------------------------------------------------------------


def _bits_to_hex(bits: list[int]) -> str:
    """Pack a list of 0/1 ints into a hex string."""
    value = 0
    for bit in bits:
        value = (value << 1) | (1 if bit else 0)
    width = (len(bits) + 3) // 4
    return f"{value:0{width}x}"


def pixel_values(image: Image.Image) -> list:
    """Return the pixel values of a single-band image.

    Pillow 12 deprecated ``Image.getdata()`` and removes it in Pillow 14
    (2027-10-15), so every call site goes through here. ``get_flattened_data``
    returns the same flat sequence for single-band images; older Pillow falls
    back to ``getdata``.
    """
    getter = getattr(image, "get_flattened_data", None)
    if getter is not None:
        return list(getter())
    return list(image.getdata())  # pragma: no cover - older Pillow only


def dhash(image: Image.Image, size: int = HASH_SIZE) -> str:
    """Difference hash: compare horizontally adjacent pixels."""
    small = image.convert("L").resize((size + 1, size), Image.LANCZOS)
    values = pixel_values(small)
    bits: list[int] = []
    for row in range(size):
        offset = row * (size + 1)
        for col in range(size):
            bits.append(1 if values[offset + col] > values[offset + col + 1] else 0)
    return _bits_to_hex(bits)


def ahash(image: Image.Image, size: int = HASH_SIZE) -> str:
    """Average hash: compare each pixel against the mean brightness."""
    small = image.convert("L").resize((size, size), Image.LANCZOS)
    values = pixel_values(small)
    mean = sum(values) / len(values)
    return _bits_to_hex([1 if p > mean else 0 for p in values])


def hamming(hex_a: str, hex_b: str, count: int = HASH_SIZE * HASH_SIZE) -> int:
    """Number of differing bits between two hex-encoded hashes."""
    if not hex_a or not hex_b:
        return count
    return (_hex_int(hex_a) ^ _hex_int(hex_b)).bit_count()


# Hex string -> int memo. Keyed by the *string value*, so (unlike an id()-keyed
# cache) it can never return another object's data. Converting once and using
# int.bit_count() also removes the 64-iteration Python loop that made the cheap
# prefilter nearly as expensive as the ZNCC it was meant to avoid.
_HEX_INT_CACHE: dict[str, int] = {}


def _hex_int(value: str) -> int:
    cached = _HEX_INT_CACHE.get(value)
    if cached is None:
        cached = int(value, 16)
        if len(_HEX_INT_CACHE) > 4096:  # bounded; hashes repeat heavily
            _HEX_INT_CACHE.clear()
        _HEX_INT_CACHE[value] = cached
    return cached


def _normalised_histogram(values: list[int], bins: int) -> list[float]:
    """Bucket 0-255 values into `bins` and normalise to sum 1."""
    counts = [0] * bins
    width = 256 / bins
    for value in values:
        index = int(value / width)
        if index >= bins:
            index = bins - 1
        counts[index] += 1
    total = sum(counts) or 1
    return [c / total for c in counts]


def histogram_1d(values: list[int], bins: int) -> list[float]:
    """Public wrapper used for hue histograms."""
    return _normalised_histogram(values, bins)


# --------------------------------------------------------------------------
# ZNCC thumbnails
# --------------------------------------------------------------------------


@dataclass
class Thumb:
    """A small normalised image plus the statistics ZNCC needs.

    ``values`` are the raw (un-normalised) pixel values; ``mean``/``std`` are
    stored so the comparison never has to recompute them, and so two reference
    images can be compared without re-reading the files.
    """

    width: int = 0
    height: int = 0
    values: list[float] = field(default_factory=list)
    mean: float = 0.0
    std: float = 0.0

    # Memoised mean-centred / L2-normalised vector used by the numpy fast path.
    # Deliberately stored *on the object* rather than in a global dict keyed by
    # id(): ids are recycled after garbage collection, so an id-keyed cache can
    # hand back another image's vector and silently produce a wrong similarity.
    # Living here also means the entry dies with the object instead of leaking.
    _vec: object = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict:
        # Stored as zlib+base64 rather than a JSON list of numbers: a 64x64x3
        # thumbnail goes from ~600 KB of JSON text to ~1 KB, which matters
        # because this file ships inside the exe and apk.
        return {
            "w": self.width,
            "h": self.height,
            "mean": round(self.mean, 3),
            "std": round(self.std, 3),
            "z": _encode_values(self.values),
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Thumb":
        if "z" in raw:
            values = _decode_values(raw.get("z", ""))
        else:  # tolerate an uncompressed list (older/hand-written files)
            values = [float(v) for v in raw.get("values", [])]
        return cls(
            width=int(raw.get("w", 0)),
            height=int(raw.get("h", 0)),
            values=values,
            mean=float(raw.get("mean", 0.0)),
            std=float(raw.get("std", 0.0)),
        )


def _encode_values(values: list[float]) -> str:
    """Quantise pixel values to bytes, then zlib+base64 them."""
    if not values:
        return ""
    raw = bytes(max(0, min(255, int(round(v)))) for v in values)
    return base64.b64encode(zlib.compress(raw, 9)).decode("ascii")


def _decode_values(blob: str) -> list[float]:
    if not blob:
        return []
    raw = zlib.decompress(base64.b64decode(blob.encode("ascii")))
    return [float(b) for b in raw]


def make_thumb(values: list[float], width: int, height: int) -> Thumb:
    """Build a Thumb, computing mean/std."""
    if not values:
        return Thumb(width=width, height=height)
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return Thumb(
        width=width, height=height, values=list(values), mean=mean, std=variance ** 0.5
    )


def thumb_from_image(image: Image.Image, size: tuple[int, int] = THUMB_SIZE) -> Thumb:
    """Greyscale thumbnail for structure matching."""
    small = image.convert("L").resize(size, Image.LANCZOS)
    return make_thumb([float(v) for v in pixel_values(small)], size[0], size[1])


def thumb_rgb(image: Image.Image, size: tuple[int, int] = THUMB_SIZE) -> Thumb:
    """Colour thumbnail flattened to a single value series (R,G,B interleaved).

    ZNCC is computed over the interleaved series, so this matches colour *and*
    structure at once.
    """
    small = image.convert("RGB").resize(size, Image.LANCZOS)
    red, green, blue = small.split()
    values: list[float] = []
    for r, g, b in zip(pixel_values(red), pixel_values(green), pixel_values(blue)):
        values.extend((float(r), float(g), float(b)))
    return make_thumb(values, size[0], size[1])


def thumb_edges(image: Image.Image, size: tuple[int, int] = (48, 48)) -> Thumb:
    """Edge-magnitude thumbnail: where the text/UI detail sits."""
    edges = image.convert("L").resize(size, Image.LANCZOS).filter(ImageFilter.FIND_EDGES)
    return make_thumb([float(v) for v in pixel_values(edges)], size[0], size[1])


try:  # numpy is on BeeWare's Android package list; the fallback keeps this
    import numpy as _np  # module importable everywhere, including bare stdlib
except Exception:  # pragma: no cover - numpy is expected but not required
    _np = None


def zncc(a: Thumb, b: Thumb) -> float:
    """Zero-normalised cross-correlation of two thumbnails, mapped to [0, 1].

    Returns 0.5 for a pair with no correlation (or with no variance at all,
    where correlation is undefined), 1.0 for a perfect match, and can go below
    0.5 for anti-correlated images (e.g. a photographic negative).
    """
    if not a.values or not b.values or len(a.values) != len(b.values):
        return 0.5
    if a.std < 1e-6 or b.std < 1e-6:
        # A flat image carries no structure to correlate.
        return 0.5

    if _np is not None:
        va = _np.asarray(a.values, dtype=_np.float32)
        vb = _np.asarray(b.values, dtype=_np.float32)
        va -= va.mean()
        vb -= vb.mean()
        denominator = float(_np.sqrt((va * va).sum()) * _np.sqrt((vb * vb).sum()))
        correlation = float((va * vb).sum() / denominator) if denominator else 0.0
    else:
        count = len(a.values)
        total = 0.0
        for x, y in zip(a.values, b.values):
            total += (x - a.mean) * (y - b.mean)
        correlation = total / (count * a.std * b.std)

    correlation = max(-1.0, min(1.0, correlation))
    return (correlation + 1.0) / 2.0


def intersection(h1: list[float], h2: list[float]) -> float:
    """Histogram intersection in [0, 1] (1 = identical distributions)."""
    if not h1 or not h2 or len(h1) != len(h2):
        return 0.0
    return sum(min(a, b) for a, b in zip(h1, h2))


def multi_channel_intersection(h1: list[float], h2: list[float], channels: int) -> float:
    """Intersection of a concatenated multi-channel histogram, normalised to [0, 1].

    ``rgb_hist`` is three concatenated per-channel histograms, each summing to 1,
    so a plain ``intersection`` returns up to 3.0 for identical images. That made
    the ``rgb_hist`` weight three times larger than its configured value and let
    ``similarity`` saturate at 1.0 - the weights in ``WEIGHTS`` did not mean what
    they said. Dividing by the channel count restores [0, 1].
    """
    if channels <= 0:
        return intersection(h1, h2)
    return intersection(h1, h2) / channels


# --------------------------------------------------------------------------
# Feature extraction
# --------------------------------------------------------------------------


def _prepare_vector(thumb: Thumb):
    """Return a mean-centred, L2-normalised numpy vector for a thumbnail.

    With both sides pre-normalised, ZNCC reduces to a single dot product, which
    is what makes the numpy path fast (a 64x64x3 comparison is 12288
    multiply-adds, done in C rather than in a Python loop).
    """
    if _np is None or not thumb.values or thumb.std < 1e-6:
        return None
    vector = _np.asarray(thumb.values, dtype=_np.float32)
    vector = vector - vector.mean()
    norm = float(_np.sqrt((vector * vector).sum()))
    if norm < 1e-9:
        return None
    return vector / norm


def _thumb_vector(thumb: Thumb):
    """Memoised normalised vector for a thumbnail (see ``Thumb._vec``)."""
    if thumb._vec is None:
        thumb._vec = _prepare_vector(thumb)
    return thumb._vec


def _zncc_fast(thumb_a: Thumb, thumb_b: Thumb) -> float:
    """Dot-product ZNCC when numpy is available, exact scalar path otherwise."""
    if _np is not None:
        va = _thumb_vector(thumb_a)
        vb = _thumb_vector(thumb_b)
        if va is None or vb is None or len(va) != len(vb):
            return 0.5
        correlation = float(_np.dot(va, vb))
        correlation = max(-1.0, min(1.0, correlation))
        return (correlation + 1.0) / 2.0
    return zncc(thumb_a, thumb_b)


@dataclass
class Features:
    """Compact descriptor of one screen image."""

    dhash: str = ""
    ahash: str = ""
    thumb_grey: Thumb = field(default_factory=Thumb)
    thumb_rgb: Thumb = field(default_factory=Thumb)
    thumb_edges: Thumb = field(default_factory=Thumb)
    rgb_hist: list[float] = field(default_factory=list)   # 3 x RGB_BINS
    hue_hist: list[float] = field(default_factory=list)   # HUE_BINS
    grid: list[float] = field(default_factory=list)       # GRID*GRID
    brightness: float = 0.0
    contrast: float = 0.0
    edge_density: float = 0.0
    structure: float = 0.0
    aspect: float = 1.0
    size: list[int] = field(default_factory=lambda: [0, 0])

    def to_dict(self) -> dict:
        return {
            "dhash": self.dhash,
            "ahash": self.ahash,
            "thumb_grey": self.thumb_grey.to_dict(),
            "thumb_rgb": self.thumb_rgb.to_dict(),
            "thumb_edges": self.thumb_edges.to_dict(),
            "rgb_hist": [round(v, 5) for v in self.rgb_hist],
            "hue_hist": [round(v, 5) for v in self.hue_hist],
            "grid": [round(v, 4) for v in self.grid],
            "brightness": round(self.brightness, 4),
            "contrast": round(self.contrast, 4),
            "edge_density": round(self.edge_density, 4),
            "structure": round(self.structure, 4),
            "aspect": round(self.aspect, 4),
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Features":
        return cls(
            dhash=raw.get("dhash", ""),
            ahash=raw.get("ahash", ""),
            thumb_grey=Thumb.from_dict(raw.get("thumb_grey") or {}),
            thumb_rgb=Thumb.from_dict(raw.get("thumb_rgb") or {}),
            thumb_edges=Thumb.from_dict(raw.get("thumb_edges") or {}),
            rgb_hist=list(raw.get("rgb_hist") or []),
            hue_hist=list(raw.get("hue_hist") or []),
            grid=list(raw.get("grid") or []),
            brightness=float(raw.get("brightness", 0.0)),
            contrast=float(raw.get("contrast", 0.0)),
            edge_density=float(raw.get("edge_density", 0.0)),
            structure=float(raw.get("structure", 0.0)),
            aspect=float(raw.get("aspect", 1.0)),
            size=list(raw.get("size") or [0, 0]),
        )


def _edge_density(image: Image.Image) -> float:
    """Fraction of pixels that look like an edge (Pillow FIND_EDGES)."""
    edges = image.convert("L").resize((128, 128), Image.LANCZOS).filter(
        ImageFilter.FIND_EDGES
    )
    edge_values = pixel_values(edges)
    threshold = 40
    strong = sum(1 for p in edge_values if p > threshold)
    return strong / (128 * 128)


def extract(image: Image.Image) -> Features:
    """Compute the full feature set for an image."""
    rgb = image.convert("RGB")
    small = rgb.resize(HIST_SIZE, Image.LANCZOS)

    red, green, blue = small.split()
    rgb_hist = (
        _normalised_histogram(pixel_values(red), RGB_BINS)
        + _normalised_histogram(pixel_values(green), RGB_BINS)
        + _normalised_histogram(pixel_values(blue), RGB_BINS)
    )

    hue = small.convert("HSV").split()[0]
    hue_hist = _normalised_histogram(pixel_values(hue), HUE_BINS)

    grey = rgb.convert("L")
    grid_img = grey.resize((GRID, GRID), Image.BOX)
    grid = [v / 255.0 for v in pixel_values(grid_img)]

    grey_small = grey.resize(HIST_SIZE, Image.LANCZOS)
    values = pixel_values(grey_small)
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)

    # Structure score: how much non-flat content the image actually has.
    # A screenshot has text and UI; a pure black frame or a lens-cap photo does
    # not, and must be declined rather than matched to something.
    contrast = (variance ** 0.5) / 128.0
    if grid:
        mean_grid = sum(grid) / len(grid)
        grid_variance = sum((g - mean_grid) ** 2 for g in grid) / len(grid)
        grid_std = grid_variance ** 0.5
    else:
        grid_std = 0.0
    structure = min(1.0, grid_std * 3.0) * 0.5 + min(1.0, contrast * 3.0) * 0.5

    width, height = image.size
    return Features(
        dhash=dhash(rgb),
        ahash=ahash(rgb),
        thumb_grey=thumb_from_image(rgb),
        thumb_rgb=thumb_rgb(rgb),
        thumb_edges=thumb_edges(rgb),
        rgb_hist=rgb_hist,
        hue_hist=hue_hist,
        grid=grid,
        brightness=mean / 255.0,
        contrast=contrast,
        edge_density=_edge_density(rgb),
        structure=round(structure, 4),
        aspect=(width / height) if height else 1.0,
        size=[width, height],
    )


def extract_path(path: str | Path) -> Features:
    """Extract features from an image file.

    For JPEGs we ask the decoder for a reduced-size draft first. A 12 MP phone
    photo otherwise costs ~1.8 s of full-resolution decode on the calling
    thread - and in the GUI that thread is the one drawing the window, so the
    app appears frozen. Features are computed at 128x128 at most, so the extra
    detail is thrown away regardless.
    """
    with Image.open(path) as handle:
        try:
            handle.draft("RGB", (512, 512))  # no-op for non-JPEG formats
        except Exception:
            pass
        handle.load()
        return extract(handle)


# --------------------------------------------------------------------------
# Similarity
# --------------------------------------------------------------------------

# Component weights. ZNCC over structure and colour carries the decision;
# the hashes and histograms act as tie-breakers. Weights were chosen against
# the synthetic photo-distortion benchmark (tools/benchmark_recognition.py).
WEIGHTS = {
    "thumb_rgb": 0.30,
    "thumb_grey": 0.22,
    "thumb_edges": 0.16,
    "dhash": 0.12,
    "rgb_hist": 0.08,
    "hue_hist": 0.05,
    "grid": 0.07,
}


def _hash_similarity(a: str, b: str) -> float:
    """Map Hamming distance to [0, 1] similarity.

    A hash with no set bits carries no information: an all-black image hashes to
    all zeros, which would otherwise "perfectly match" any mostly-dark screen.
    Such degenerate hashes are reported as uninformative (0.5) instead.
    """
    if not a or not b:
        return 0.5
    ia, ib = _hex_int(a), _hex_int(b)
    if ia == 0 or ib == 0:
        return 0.5
    distance = (ia ^ ib).bit_count()
    return max(0.0, 1.0 - distance / 64.0)


def _list_similarity(a: list[float], b: list[float]) -> float:
    """1 - mean absolute difference, clamped to [0, 1]."""
    if not a or not b or len(a) != len(b):
        return 0.0
    diff = sum(abs(x - y) for x, y in zip(a, b)) / len(a)
    return max(0.0, 1.0 - diff)


def similarity(a: Features, b: Features) -> float:
    """Weighted similarity of two feature sets, in [0, 1]."""
    parts = components(a, b)
    total_weight = sum(WEIGHTS.values())
    score = sum(parts[key] * WEIGHTS[key] for key in WEIGHTS) / total_weight
    return max(0.0, min(1.0, score))


def components(a: Features, b: Features) -> dict[str, float]:
    """Per-component similarity, keyed by feature name, each in [0, 1]."""
    return {
        "thumb_rgb": _zncc_fast(a.thumb_rgb, b.thumb_rgb),
        "thumb_grey": _zncc_fast(a.thumb_grey, b.thumb_grey),
        "thumb_edges": _zncc_fast(a.thumb_edges, b.thumb_edges),
        "dhash": _hash_similarity(a.dhash, b.dhash),
        "rgb_hist": multi_channel_intersection(a.rgb_hist, b.rgb_hist, RGB_CHANNELS),
        "hue_hist": intersection(a.hue_hist, b.hue_hist),
        "grid": _list_similarity(a.grid, b.grid),
    }


def cheap_score(a: Features, b: Features) -> float:
    """A cheap upper-bound-ish score used to prefilter candidates.

    Uses only the 64-bit hashes and the small histograms - no per-pixel work -
    so it can be run against every reference before paying for ZNCC on the few
    that survive. This is what keeps recognition fast without numpy.
    """
    return (
        _hash_similarity(a.dhash, b.dhash) * 0.45
        + _hash_similarity(a.ahash, b.ahash) * 0.15
        + multi_channel_intersection(a.rgb_hist, b.rgb_hist, RGB_CHANNELS) * 0.20
        + intersection(a.hue_hist, b.hue_hist) * 0.10
        + _list_similarity(a.grid, b.grid) * 0.10
    )


_COMPONENT_LABELS = {
    "thumb_rgb": "画面结构+配色",
    "thumb_grey": "画面结构",
    "thumb_edges": "文字/元素分布",
    "dhash": "布局指纹",
    "rgb_hist": "配色分布",
    "hue_hist": "色相分布",
    "grid": "版面明暗",
}


def explain(a: Features, b: Features) -> list[tuple[str, float]]:
    """Per-component similarity with Chinese labels, best first."""
    parts = components(a, b)
    labelled = [(_COMPONENT_LABELS.get(key, key), value) for key, value in parts.items()]
    return sorted(labelled, key=lambda kv: -kv[1])


# --------------------------------------------------------------------------
# Reference library I/O
# --------------------------------------------------------------------------


@dataclass
class Reference:
    """One labelled reference image."""

    label: str          # class id, e.g. "recovery-menu"
    title: str          # human name, e.g. "Recovery 主菜单"
    kb_slug: str        # knowledge-base page to open
    source: str         # "synthetic" or "user"
    path: str = ""      # reference image path (relative), for display
    features: Features = field(default_factory=Features)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "title": self.title,
            "kb_slug": self.kb_slug,
            "source": self.source,
            "path": self.path,
            "features": self.features.to_dict(),
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Reference":
        return cls(
            label=raw.get("label", ""),
            title=raw.get("title", ""),
            kb_slug=raw.get("kb_slug", ""),
            source=raw.get("source", ""),
            path=raw.get("path", ""),
            features=Features.from_dict(raw.get("features") or {}),
        )


@dataclass
class ReferenceLibrary:
    """A set of labelled reference screens."""

    version: int = FEATURE_VERSION
    references: list[Reference] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "feature_version": self.version,
            "count": len(self.references),
            "references": [r.to_dict() for r in self.references],
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "ReferenceLibrary":
        return cls(
            version=int(raw.get("feature_version", FEATURE_VERSION)),
            references=[Reference.from_dict(item) for item in raw.get("references", [])],
        )

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "ReferenceLibrary":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def labels(self) -> list[str]:
        seen: list[str] = []
        for reference in self.references:
            if reference.label not in seen:
                seen.append(reference.label)
        return seen
