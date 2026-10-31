"""把色带数组画成像素矩阵，支持五种排列方式。

横向 / 纵向 / 斜向用「累积和 + 区间平均」的方式直接生成整行像素，
同心圆 / 螺旋用径向或角度参数查表。这样即使一条色带不足 1 像素，
也能得到均匀的混色，而不是锯齿。
"""
from __future__ import annotations

import math

import numpy as np


def _cumulative(colors: np.ndarray) -> np.ndarray:
    return np.vstack(
        (np.zeros((1, 3), dtype=np.float64), np.cumsum(colors, axis=0, dtype=np.float64))
    )


def _range_colors(
    cum: np.ndarray, n: int, lo: np.ndarray, hi: np.ndarray
) -> np.ndarray:
    """返回 [lo, hi) 区间内的平均颜色，lo/hi 是色带索引（浮点）。"""
    lo = np.clip(lo, 0, n)
    hi = np.clip(hi, 0, n)
    span = np.maximum(hi - lo, 1e-9)
    xp = np.arange(n + 1, dtype=np.float64)
    out = np.empty((len(lo), 3), dtype=np.float64)
    for c in range(3):
        out[:, c] = np.interp(hi, xp, cum[:, c]) - np.interp(lo, xp, cum[:, c])
    out /= span[:, None]
    return np.clip(out, 0, 255).astype(np.uint8)


def _linear_lut(n: int, bins: int) -> np.ndarray:
    lo = np.arange(bins, dtype=np.float64) * n / bins
    hi = (np.arange(bins, dtype=np.float64) + 1) * n / bins
    return lo, hi


def _horizontal(colors, width, height):
    lo, hi = _linear_lut(len(colors), width)
    cols = _range_colors(_cumulative(colors), len(colors), lo, hi)
    return np.ascontiguousarray(np.repeat(cols[None, :, :], height, axis=0))


def _vertical(colors, width, height):
    lo, hi = _linear_lut(len(colors), height)
    rows = _range_colors(_cumulative(colors), len(colors), lo, hi)
    return np.ascontiguousarray(np.repeat(rows[:, None, :], width, axis=1))


def _diagonal(colors, width, height):
    cum = _cumulative(colors)
    n = len(colors)
    bins = width + height - 1
    lo, hi = _linear_lut(n, bins)
    lut = _range_colors(cum, n, lo, hi)
    img = np.empty((height, width, 3), dtype=np.uint8)
    for y in range(height):
        img[y] = lut[y : y + width]
    return img


def _rings(colors, width, height):
    cum = _cumulative(colors)
    n = len(colors)
    radius = math.hypot(width / 2, height / 2)
    bins = int(max(2048, min(8192, math.ceil(radius * 2))))
    lo, hi = _linear_lut(n, bins)
    lut = _range_colors(cum, n, lo, hi)

    cx, cy = width / 2, height / 2
    dx = np.arange(width, dtype=np.float64) - cx
    dx2 = dx * dx
    img = np.empty((height, width, 3), dtype=np.uint8)
    scale = bins / radius
    for y in range(height):
        dy = y - cy
        r = np.sqrt(dx2 + dy * dy)
        idx = np.floor(r * scale).astype(np.int32)
        np.clip(idx, 0, bins - 1, out=idx)
        img[y] = lut[idx]
    return img


def _spiral(colors, width, height, turns: int):
    cum = _cumulative(colors)
    n = len(colors)
    radius = math.hypot(width / 2, height / 2)
    bins = int(max(2048, min(8192, n * 2)))
    lo, hi = _linear_lut(n, bins)
    lut = _range_colors(cum, n, lo, hi)

    cx, cy = width / 2, height / 2
    dx = np.arange(width, dtype=np.float64) - cx
    two_pi = 2 * math.pi
    img = np.empty((height, width, 3), dtype=np.uint8)
    for y in range(height):
        dy = y - cy
        r = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx) % two_pi
        turns_f = max(2, int(turns))
        k = np.floor(r / radius * turns_f - theta / two_pi)
        u = (theta / two_pi + k) / turns_f
        u = np.clip(u, 0, 1)
        idx = np.floor(u * bins).astype(np.int32)
        np.clip(idx, 0, bins - 1, out=idx)
        img[y] = lut[idx]
    return img


def build_canvas(
    colors: np.ndarray, width: int, height: int, layout: str, spiral_turns: int = 5
) -> np.ndarray:
    if len(colors) == 0:
        return np.zeros((height, width, 3), dtype=np.uint8)
    if layout == "vertical":
        return _vertical(colors, width, height)
    if layout == "diagonal":
        return _diagonal(colors, width, height)
    if layout == "rings":
        return _rings(colors, width, height)
    if layout == "spiral":
        return _spiral(colors, width, height, spiral_turns)
    return _horizontal(colors, width, height)


def hex_to_rgb(hexes: list[str]) -> np.ndarray:
    if not hexes:
        return np.zeros((0, 3), dtype=np.uint8)
    arr = np.array(
        [[int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)] for h in hexes],
        dtype=np.uint8,
    )
    return arr
