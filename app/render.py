"""色带成图 + 后处理（标题 / 噪点 / 虚化）。"""
from __future__ import annotations

import io
import math
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import fonts, layout

ANCHOR_ROWS = ("top", "middle", "bottom")
ANCHOR_COLS = ("left", "center", "right")


def normalize_post(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}

    def num(key: str, default: float, low: float, high: float) -> float:
        try:
            value = float(raw.get(key, default))
        except (TypeError, ValueError):
            value = default
        return round(max(low, min(high, value)), 3)

    anchor = str(raw.get("anchor", "middle-center"))
    if anchor not in {f"{r}-{c}" for r in ANCHOR_ROWS for c in ANCHOR_COLS}:
        anchor = "middle-center"

    color = str(raw.get("color", "#ffffff"))
    if not (color.startswith("#") and len(color) in (4, 7)):
        color = "#ffffff"

    return {
        "title": str(raw.get("title", ""))[:120],
        "subtitle": str(raw.get("subtitle", ""))[:120],
        "font": str(raw.get("font", "noto-serif")),
        "sizePct": num("sizePct", 7.0, 1.0, 30.0),
        "trackingPct": num("trackingPct", 4.0, 0.0, 40.0),
        "color": color,
        "opacity": num("opacity", 100.0, 0.0, 100.0),
        "anchor": anchor,
        "offsetX": num("offsetX", 0.0, -60.0, 60.0),
        "offsetY": num("offsetY", 0.0, -60.0, 60.0),
        "noise": num("noise", 0.0, 0.0, 100.0),
        "grain": num("grain", 2.0, 1.0, 12.0),
        "mono": bool(raw.get("mono", True)),
        "blur": num("blur", 0.0, 0.0, 60.0),
    }


def _hex_rgba(color: str, opacity: float) -> tuple[int, int, int, int]:
    if len(color) == 4:
        color = "#" + "".join(ch * 2 for ch in color[1:])
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    return r, g, b, int(round(max(0, min(100, opacity)) * 255 / 100))


def _load_font(key: str, size: int) -> ImageFont.FreeTypeFont:
    path, index = fonts.resolve_font(key)
    size = max(4, int(size))
    if path:
        try:
            return ImageFont.truetype(path, size, index=index)
        except Exception:  # noqa: BLE001
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                pass
    try:
        return ImageFont.load_default(size=size)  # type: ignore[call-arg]
    except TypeError:
        return ImageFont.load_default()  # type: ignore[return-value]


def _measure(text: str, font, tracking: float) -> float:
    if not text:
        return 0.0
    width = sum(font.getlength(ch) for ch in text)
    return width + tracking * max(0, len(text) - 1)


def _draw_tracked(draw, text, font, fill, tracking, x, baseline):
    cursor = x
    for ch in text:
        draw.text((cursor, baseline), ch, font=font, fill=fill, anchor="ls")
        cursor += font.getlength(ch) + tracking


def _apply_title(img: Image.Image, post: dict[str, Any]) -> Image.Image:
    title = post["title"]
    subtitle = post["subtitle"]
    if not title and not subtitle:
        return img

    width, height = img.size
    main_size = max(6, int(round(height * post["sizePct"] / 100)))
    main_font = _load_font(post["font"], main_size)
    tracking = main_size * post["trackingPct"] / 100

    sub_font = None
    sub_size = max(5, int(round(main_size * 0.24)))
    sub_tracking = max(1.0, sub_size * 0.5)
    if subtitle:
        sub_font = _load_font(post["font"], sub_size)

    main_metrics = main_font.getmetrics()
    main_h = sum(main_metrics)
    sub_h = 0
    if sub_font is not None:
        sub_metrics = sub_font.getmetrics()
        sub_h = sum(sub_metrics)

    gap = int(main_size * 0.55) if subtitle else 0
    block_h = main_h + (gap + sub_h if subtitle else 0)

    row, col = post["anchor"].split("-")
    ax = {"left": width * 0.07, "center": width / 2, "right": width * 0.93}[col]
    ay = {"top": height * 0.12, "middle": height / 2, "bottom": height * 0.88}[row]
    ax += width * post["offsetX"] / 100
    ay += height * post["offsetY"] / 100

    top = {"top": ay, "middle": ay - block_h / 2, "bottom": ay - block_h}[row]

    fill = _hex_rgba(post["color"], post["opacity"])
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if title:
        w = _measure(title, main_font, tracking)
        x = {"left": ax, "center": ax - w / 2, "right": ax - w}[col]
        _draw_tracked(
            draw, title, main_font, fill, tracking, x, top + main_metrics[0]
        )

    if subtitle and sub_font is not None:
        w = _measure(subtitle, sub_font, sub_tracking)
        x = {"left": ax, "center": ax - w / 2, "right": ax - w}[col]
        baseline = top + main_h + gap + sub_metrics[0]
        _draw_tracked(
            draw, subtitle, sub_font, fill, sub_tracking, x, baseline
        )

    base = img.convert("RGBA")
    return Image.alpha_composite(base, overlay).convert("RGB")


def _noise_delta(width: int, height: int, grain: float, sigma: float) -> np.ndarray:
    """生成一张低分辨率噪声再放大，避免逐像素随机（大画面下快一个数量级）。"""
    grain_px = max(1, int(round(grain)))
    gw = max(2, int(math.ceil(width / grain_px)) + 2)
    gh = max(2, int(math.ceil(height / grain_px)) + 2)
    rng = np.random.default_rng()
    noise = rng.normal(0.0, 1.0, (gh, gw)).astype(np.float32)
    small = np.clip(noise * 40 + 128, 0, 255).astype(np.uint8)
    upscaled = np.asarray(
        Image.fromarray(small, mode="L").resize((width, height), Image.BILINEAR),
        dtype=np.float32,
    )
    return ((upscaled - 128.0) / 40.0 * sigma).round().astype(np.int16)


def _apply_noise(
    arr: np.ndarray, strength: float, grain: float, mono: bool
) -> np.ndarray:
    height, width = arr.shape[:2]
    sigma = strength * 0.45
    delta = _noise_delta(width, height, grain, sigma)

    if mono:
        # 单场噪声加到三个通道，一次广播完成，避免三遍全图运算
        return np.clip(arr.astype(np.int16) + delta[:, :, None], 0, 255).astype(
            np.uint8
        )

    base = arr.astype(np.int16)
    for c in range(3):
        base[:, :, c] = np.clip(
            base[:, :, c] + _noise_delta(width, height, grain, sigma), 0, 255
        )
    return base.astype(np.uint8)


def build_base(
    colors: np.ndarray,
    options: dict[str, Any],
    scale: float = 1.0,
) -> Image.Image:
    """只依赖色带与排列方式的底图，供多次后处理复用。"""
    width = max(2, int(round(options["width"] * scale)))
    height = max(2, int(round(options["height"] * scale)))
    canvas = layout.build_canvas(
        colors, width, height, options["layout"], options.get("spiralTurns", 5)
    )
    return Image.fromarray(canvas, mode="RGB")


def render_image(
    colors: np.ndarray,
    options: dict[str, Any],
    post: dict[str, Any],
    scale: float = 1.0,
    base: Image.Image | None = None,
) -> Image.Image:
    img = base.copy() if base is not None else build_base(colors, options, scale)

    blur = post["blur"] * scale
    if blur > 0.2:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur))

    if post["noise"] > 0:
        arr = np.asarray(img)
        arr = _apply_noise(
            arr,
            post["noise"],
            max(1, post["grain"] * scale),
            post["mono"],
        )
        img = Image.fromarray(arr, mode="RGB")

    if post["title"] or post["subtitle"]:
        img = _apply_title(img, post)

    return img


def render_png(
    colors: np.ndarray,
    options: dict[str, Any],
    post: dict[str, Any],
    scale: float = 1.0,
    base: Image.Image | None = None,
    compress_level: int = 6,
) -> bytes:
    img = render_image(colors, options, post, scale, base)
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=compress_level)
    return buf.getvalue()


def font_preview_png(key: str, text: str, size: int = 76) -> bytes:
    text = (text or "电影色带")[:24]
    size = max(12, min(160, int(size)))
    width = 720
    height = 200
    limit = width - 48

    # 长文本按比例缩小字号，避免超出预览画布
    font = _load_font(key, size)
    tracking = size * 0.08
    tw = _measure(text, font, tracking)
    if tw > limit:
        size = max(10, int(size * limit / tw))
        font = _load_font(key, size)
        tracking = size * 0.08
        tw = _measure(text, font, tracking)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    metrics = font.getmetrics()
    x = max(16, (width - tw) / 2)
    baseline = height / 2 + (metrics[0] - metrics[1]) / 2
    _draw_tracked(draw, text, font, (240, 236, 228, 255), tracking, x, baseline)

    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=6)
    return buf.getvalue()
