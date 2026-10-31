"""把用户参数换算成可执行的采样计划。"""
from __future__ import annotations

import math
from typing import Any

LAYOUTS = ("horizontal", "vertical", "rings", "diagonal", "spiral")
MAX_BANDS = 30000


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_options(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    layout = raw.get("layout", "horizontal")
    if layout not in LAYOUTS:
        layout = "horizontal"
    return {
        "interval": round(_clamp(float(raw.get("interval", 2.0)), 0.2, 60.0), 3),
        "bandWidth": round(_clamp(float(raw.get("bandWidth", 2.0)), 0.25, 40.0), 3),
        "layout": layout,
        "width": int(_clamp(float(raw.get("width", 2560)), 64, 8192)),
        "height": int(_clamp(float(raw.get("height", 800)), 64, 8192)),
        "spiralTurns": int(_clamp(float(raw.get("spiralTurns", 5)), 2, 16)),
        "autoCrop": bool(raw.get("autoCrop", True)),
    }


def canvas_extent(width: int, height: int, layout: str) -> float:
    """色带沿排布方向可用的总长度（像素）。"""
    if layout == "horizontal":
        return float(width)
    if layout == "vertical":
        return float(height)
    if layout == "diagonal":
        return (width + height) / math.sqrt(2)
    return math.hypot(width / 2, height / 2)


def build_plan(videos: list[dict[str, Any]], options: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    per_video: list[dict[str, Any]] = []
    total = 0.0

    for index, video in enumerate(videos):
        duration = max(0.0, float(video.get("duration", 0)))
        skip_start = max(0.0, float(video.get("skipStart", 0))) * 60
        skip_end = max(0.0, float(video.get("skipEnd", 0))) * 60
        start = min(skip_start, duration)
        end = max(0.0, duration - skip_end)
        trimmed = max(0.0, end - start)
        name = video.get("name") or f"视频 {index + 1}"
        if trimmed < 1.0:
            warnings.append(f"《{name}》去掉片头/片尾后不足 1 秒，将被忽略")
        per_video.append(
            {
                "index": index,
                "name": name,
                "path": video.get("path", ""),
                "duration": duration,
                "start": start,
                "trimmed": trimmed,
                "skipStart": skip_start / 60,
                "skipEnd": skip_end / 60,
            }
        )
        total += trimmed

    opts = normalize_options(options)
    extent = canvas_extent(opts["width"], opts["height"], opts["layout"])
    capacity = max(1, int(math.floor(extent / opts["bandWidth"])))

    by_interval = max(1, int(math.floor(total / opts["interval"]))) if total > 0 else 0
    bands = min(by_interval, capacity, MAX_BANDS) if total > 0 else 0

    if bands:
        limited_by = "interval"
        if bands >= capacity:
            limited_by = "capacity"
        if bands >= MAX_BANDS:
            limited_by = "max"
        weights = [v["trimmed"] for v in per_video]
        allocated = 0
        for i, v in enumerate(per_video):
            if i == len(per_video) - 1:
                v["bands"] = max(0, bands - allocated)
            else:
                share = bands * (v["trimmed"] / total) if total else 0
                v["bands"] = int(round(share))
                allocated += v["bands"]
            v["interval"] = (
                v["trimmed"] / v["bands"] if v["bands"] else 0.0
            )
    else:
        limited_by = "empty"
        for v in per_video:
            v["bands"] = 0
            v["interval"] = 0.0

    return {
        "options": opts,
        "totalDuration": round(total, 2),
        "bands": bands,
        "capacity": capacity,
        "byInterval": by_interval,
        "limitedBy": limited_by,
        "effectiveInterval": round(total / bands, 3) if bands else 0.0,
        "bandPixels": round(extent / bands, 2) if bands else 0.0,
        "perVideo": per_video,
        "warnings": warnings,
    }
