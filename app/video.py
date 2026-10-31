"""视频探测与主色调采样。

采用 ffmpeg 把视频降采样到 64x64 后用 numpy 求均值：
- 解码是瓶颈，缩放本身几乎无成本；
- 长视频按时间切片并行解码，并保持切片顺序输出，保证色带顺序正确。
"""
from __future__ import annotations

import json
import hashlib
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

SAMPLE_SIZE = 64
FRAME_BYTES = SAMPLE_SIZE * SAMPLE_SIZE * 3

_probe_cache: dict[tuple[str, int, int], "VideoInfo"] = {}
_crop_cache: dict[str, tuple[int, int, int, int] | None] = {}
_probe_lock = threading.Lock()

if getattr(sys, "frozen", False):
    _DATA_DIR = Path(sys.executable).resolve().parent
else:
    _DATA_DIR = Path(__file__).resolve().parent.parent

CACHE_FILE = _DATA_DIR / ".cache" / "crop.json"
SAMPLE_CACHE_DIR = _DATA_DIR / ".cache" / "samples"
_crop_loaded = False


# 密集采样缓存：解码量只取决于片源帧率，与输出条数无关，
# 因此统一按固定密度落盘；任何条数/排列需求都从密集结果瞬间重采样
DENSE_RATE = 2.0  # 条/秒


def _sample_cache_key(
    info: "VideoInfo",
    start: float,
    trim_duration: float,
    crop: tuple[int, int, int, int] | None,
) -> str:
    stat = os.stat(info.path)
    raw = "|".join(
        [
            info.path,
            str(int(stat.st_mtime)),
            str(stat.st_size),
            f"{start:.3f}",
            f"{trim_duration:.3f}",
            "-".join(str(v) for v in crop) if crop else "nocrop",
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _load_sample(key: str) -> dict | None:
    try:
        data = json.loads(
            (SAMPLE_CACHE_DIR / f"{key}.json").read_text("utf-8")
        )
        if (
            isinstance(data, dict)
            and isinstance(data.get("colors"), list)
            and data.get("rate", 0) > 0
        ):
            os.utime(SAMPLE_CACHE_DIR / f"{key}.json")  # LRU：命中即续期
            return data
    except Exception:  # noqa: BLE001
        pass
    return None


def _save_sample(key: str, rate: float, colors: list[str]) -> None:
    try:
        SAMPLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (SAMPLE_CACHE_DIR / f"{key}.json").write_text(
            json.dumps({"rate": round(rate, 4), "colors": colors}),
            encoding="utf-8",
        )
        files = sorted(
            SAMPLE_CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime
        )
        for stale in files[:-120]:
            stale.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass


def _resample(colors: list[str], bands: int) -> list[str]:
    """把密集颜色均分成 bands 组，每组求平均色。"""
    n = len(colors)
    if n == 0 or bands <= 0:
        return []
    if bands >= n:
        return list(colors[:bands]) if bands == n else colors + colors[-1:] * (bands - n)
    arr = np.empty((n, 3), dtype=np.float32)
    for i, c in enumerate(colors):
        arr[i, 0] = int(c[1:3], 16)
        arr[i, 1] = int(c[3:5], 16)
        arr[i, 2] = int(c[5:7], 16)
    bounds = np.linspace(0, n, bands + 1).astype(np.int64)
    out: list[str] = []
    for i in range(bands):
        seg = arr[bounds[i] : max(bounds[i] + 1, bounds[i + 1])]
        mean = seg.mean(axis=0).round().clip(0, 255).astype(np.int64)
        out.append(f"#{mean[0]:02x}{mean[1]:02x}{mean[2]:02x}")
    return out


def _load_crop_cache() -> None:
    """黑边检测结果落盘，重启后无需再次解码探测。"""
    global _crop_loaded
    if _crop_loaded:
        return
    _crop_loaded = True
    try:
        data = json.loads(CACHE_FILE.read_text("utf-8"))
    except Exception:  # noqa: BLE001
        return
    for key, value in data.items():
        _crop_cache[key] = tuple(value) if value else None


def _save_crop_cache() -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        items = list(_crop_cache.items())[-300:]
        CACHE_FILE.write_text(
            json.dumps(dict(items), ensure_ascii=False), encoding="utf-8"
        )
    except Exception:  # noqa: BLE001
        pass


@dataclass
class VideoInfo:
    path: str
    name: str
    duration: float
    width: int
    height: int
    fps: float
    size: int
    codec: str = ""


def _ffmpeg_info(path: str) -> str:
    try:
        proc = subprocess.run(
            [FFMPEG, "-hide_banner", "-i", path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=40,
        )
        return (proc.stderr or "") + (proc.stdout or "")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"无法读取视频信息：{exc}") from exc


def _parse_duration(text: str) -> float:
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if m:
        h, mnt, sec = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + mnt * 60 + sec
    return 0.0


def _cv2_fallback(path: str) -> tuple[float, int, int, float]:
    try:
        import cv2  # type: ignore

        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        cap.release()
        duration = frames / fps if fps > 0 else 0.0
        return duration, width, height, fps
    except Exception:  # noqa: BLE001
        return 0.0, 0, 0, 0.0


def probe_video(path: str) -> VideoInfo:
    p = str(Path(path))
    if not os.path.isfile(p):
        raise FileNotFoundError(f"文件不存在：{p}")

    stat = os.stat(p)
    key = (p, int(stat.st_mtime), int(stat.st_size))
    with _probe_lock:
        cached = _probe_cache.get(key)
        if cached is not None:
            return cached

    info = _ffmpeg_info(p)
    duration = _parse_duration(info)
    width = height = 0
    fps = 0.0
    codec = ""

    video_lines = [ln for ln in info.splitlines() if "Video:" in ln and "Stream #" in ln]
    if video_lines:
        line = video_lines[0]
        size_m = re.search(r"(\d{2,5})x(\d{2,5})", line)
        if size_m:
            width, height = int(size_m.group(1)), int(size_m.group(2))
        fps_m = re.search(r"(\d+(?:\.\d+)?)\s+fps", line)
        if not fps_m:
            fps_m = re.search(r"(\d+(?:\.\d+)?)\s+tbr", line)
        if fps_m:
            fps = float(fps_m.group(1))
        codec_m = re.search(r"Video:\s*(\w+)", line)
        if codec_m:
            codec = codec_m.group(1)

    if duration <= 0 or width <= 0:
        d2, w2, h2, fps2 = _cv2_fallback(p)
        duration = duration or d2
        width = width or w2
        height = height or h2
        fps = fps or fps2

    if duration <= 0:
        raise RuntimeError("无法获取视频时长，可能该文件不是有效视频")

    result = VideoInfo(
        path=p,
        name=Path(p).name,
        duration=float(duration),
        width=int(width),
        height=int(height),
        fps=round(float(fps), 3),
        size=int(stat.st_size),
        codec=codec,
    )
    with _probe_lock:
        _probe_cache[key] = result
    return result


@dataclass
class Segment:
    start: float
    duration: float
    bands: int
    fps: float


def detect_crop(info: VideoInfo) -> tuple[int, int, int, int] | None:
    """检测电影黑边，返回 (w, h, x, y)。无明显黑边时返回 None。"""
    stat = os.stat(info.path)
    key = f"{info.path}|{int(stat.st_mtime)}|{stat.st_size}"
    _load_crop_cache()
    with _probe_lock:
        if key in _crop_cache:
            return _crop_cache[key]

    # 只取开头 10 秒（跳过前 3 秒防止片头全黑），黑边是恒定值，无需整段扫描
    sample = min(10.0, max(2.0, info.duration))
    seek = 3.0 if info.duration > 16 else 0.0
    crop: tuple[int, int, int, int] | None = None
    try:
        cmd = [
            FFMPEG,
            "-hide_banner",
            "-threads",
            str(max(1, (os.cpu_count() or 4) // 2)),
        ]
        if seek:
            cmd += ["-ss", f"{seek:.2f}"]
        cmd += [
            "-i",
            info.path,
            "-t",
            f"{sample:.2f}",
            "-vf",
            "fps=2,cropdetect=limit=24:round=2:reset=0",
            "-f",
            "null",
            "-",
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120,
        )
        matches = re.findall(
            r"crop=(\d+):(\d+):(\d+):(\d+)", proc.stderr or ""
        )
        if matches:
            w, h, x, y = (int(v) for v in matches[-1])
            src_area = max(1, info.width * info.height)
            if 0.5 <= (w * h) / src_area < 0.985:
                crop = (w, h, x, y)
    except Exception:  # noqa: BLE001
        crop = None

    with _probe_lock:
        _crop_cache[key] = crop
        _save_crop_cache()
    return crop


def plan_segments(start: float, duration: float, bands: int) -> list[Segment]:
    """把一段要采样的区间切成若干片，便于并行解码。"""
    if duration <= 0 or bands <= 0:
        return []

    max_chunk = 180.0  # 3 分钟一片：进度更新更细，也利于并行
    count = int(math.ceil(duration / max_chunk))
    count = max(1, min(count, 48))
    if count == 1:
        return [Segment(start, duration, bands, bands / duration)]

    weights = [duration / count] * count
    weights[-1] = duration - sum(weights[:-1])

    seg_bands: list[int] = []
    allocated = 0
    for i, w in enumerate(weights):
        if i == len(weights) - 1:
            b = bands - allocated
        else:
            b = int(round(bands * w / duration))
            allocated += b
        seg_bands.append(max(0, b))

    segs: list[Segment] = []
    t = start
    for w, b in zip(weights, seg_bands):
        if b > 0 and w > 0:
            segs.append(Segment(t, w, b, b / w))
        t += w
    return segs


def _build_cmd(
    seg: Segment,
    path: str,
    crop: tuple[int, int, int, int] | None = None,
    threads: int = 0,
    hwaccel: bool = True,
) -> list[str]:
    filters = [f"fps={seg.fps:.6f}"]
    if crop:
        filters.append("crop={}:{}:{}:{}".format(*crop))
    filters.append(f"scale={SAMPLE_SIZE}:{SAMPLE_SIZE}:flags=area")
    vf = ",".join(filters)
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
    ]
    # 能用 GPU 解码就用（auto 会自动回退软件解码）
    if hwaccel:
        cmd += ["-hwaccel", "auto"]
    # 平均色只需要参考帧就够了：跳过非参考帧可省约一半解码量
    cmd += ["-skip_frame", "noref"]
    # 多个切片并行时按核数分摊线程，避免多进程争抢同一批核心
    if threads > 0:
        cmd += ["-threads", str(threads)]
    cmd += [
        "-ss",
        f"{seg.start:.3f}",
        "-t",
        f"{seg.duration:.3f}",
        "-i",
        path,
        "-map",
        "0:v:0",
        "-an",
        "-sn",
        "-vf",
        vf,
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-vsync",
        "0",
        "pipe:1",
    ]
    return cmd


# 记住每种编码格式的硬件解码可用性，避免每个切片都白白重跑一遍
_hwaccel_ok: dict[str, bool] = {}
_hw_lock = threading.Lock()


def _segment_colors(
    seg: Segment,
    path: str,
    cancel: threading.Event,
    crop: tuple[int, int, int, int] | None = None,
    threads: int = 0,
    hwaccel: bool = True,
    codec: str = "",
) -> list[str]:
    try:
        return _run_segment(seg, path, cancel, crop, threads, hwaccel)
    except RuntimeError:
        if not hwaccel or cancel.is_set():
            raise
        # 显卡解码不可用时退回纯软件解码，并记住结果
        with _hw_lock:
            _hwaccel_ok[codec] = False
        return _run_segment(seg, path, cancel, crop, threads, False)


def _run_segment(
    seg: Segment,
    path: str,
    cancel: threading.Event,
    crop: tuple[int, int, int, int] | None,
    threads: int,
    hwaccel: bool,
) -> list[str]:
    with tempfile.TemporaryFile() as errf:
        proc = subprocess.Popen(
            _build_cmd(seg, path, crop, threads, hwaccel),
            stdout=subprocess.PIPE,
            stderr=errf,
            stdin=subprocess.DEVNULL,
        )
        colors: list[str] = []
        try:
            assert proc.stdout is not None
            leftover = b""
            while not cancel.is_set():
                chunk = proc.stdout.read(FRAME_BYTES * 8)
                if not chunk:
                    break
                leftover += chunk
                n = len(leftover) // FRAME_BYTES
                if n == 0:
                    continue
                data = np.frombuffer(leftover[: n * FRAME_BYTES], dtype=np.uint8)
                data = data.reshape(n, SAMPLE_SIZE * SAMPLE_SIZE, 3)
                means = data.mean(axis=1)
                means = np.clip(means, 0, 255).astype(np.uint8)
                colors.extend(
                    f"#{int(r):02x}{int(g):02x}{int(b):02x}"
                    for r, g, b in means
                )
                leftover = leftover[n * FRAME_BYTES:]
            proc.stdout.close()
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()

        if not colors:
            errf.seek(0)
            message = errf.read().decode("utf-8", "ignore").strip()
            if cancel.is_set():
                return []
            raise RuntimeError(message or "视频解码失败（未取到任何画面）")
        return colors


def extract_video(
    info: VideoInfo,
    start: float,
    trim_duration: float,
    bands: int,
    on_bands,
    cancel: threading.Event,
    crop: tuple[int, int, int, int] | None = None,
) -> None:
    """按时间顺序回调该视频的色带（十六进制颜色）。"""
    if trim_duration <= 0 or bands <= 0:
        return

    # 密集缓存命中 → 重采样即可，零解码（换排列/条数/间隔都走这里）
    key = _sample_cache_key(info, start, trim_duration, crop)
    need_rate = bands / trim_duration
    cached = _load_sample(key)
    if cached is not None and cached["rate"] + 1e-6 >= need_rate:
        colors = _resample(cached["colors"], bands)
        for i in range(0, len(colors), 256):
            if cancel.is_set():
                return
            on_bands(colors[i : i + 256])
        return

    # 以不低于密集密度的速率解码；fps 过滤器的解码量只与片源帧率有关，
    # 输出密度再高也几乎不增加开销，却让缓存对任何条数都通用
    decode_rate = max(need_rate, DENSE_RATE)
    dense_bands = max(bands, int(math.ceil(trim_duration * decode_rate)))
    segs = plan_segments(start, trim_duration, dense_bands)
    if not segs:
        return

    cpu = os.cpu_count() or 4
    # 实测 h264 走 hwaccel 后每帧 GPU→内存拷贝开销反而比纯软件解码慢数倍，
    # 只对软件解码很贵的 HEVC 启用；失败过一次就永久记住改走软件
    default_hw = info.codec.lower() in ("hevc", "h265")
    hwaccel = _hwaccel_ok.get(info.codec, default_hw)

    def emit(colors: list[str]) -> None:
        for i in range(0, len(colors), 64):
            if cancel.is_set():
                return
            on_bands(colors[i : i + 64])

    if len(segs) == 1:
        dense = _segment_colors(
            segs[0], info.path, cancel, crop,
            threads=max(1, min(16, cpu)), hwaccel=hwaccel, codec=info.codec,
        )
        if cancel.is_set():
            return
        _save_sample(key, decode_rate, dense)
        emit(_resample(dense, bands))
        return

    # 切片越多越能压满多核；线程数按实际并发数分摊，避免互相抢核
    workers = max(1, min(8, cpu // 2, len(segs)))
    threads = max(2, min(16, cpu // workers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                _segment_colors, seg, info.path, cancel, crop, threads,
                hwaccel, info.codec,
            )
            for seg in segs
        ]
        merged: list[str] = []
        allocated = 0
        for idx, future in enumerate(futures):  # 按切片顺序消费，时间线不乱
            if cancel.is_set():
                for f in futures:
                    f.cancel()
                return
            dense = future.result()
            merged.extend(dense)
            # 把该切片的密集结果折算成它应占的色带数，流式推进进度
            if idx == len(futures) - 1:
                share = bands - allocated
            else:
                share = int(round(bands * segs[idx].duration / trim_duration))
            allocated += share
            if share > 0:
                emit(_resample(dense, share))
        if not cancel.is_set():
            _save_sample(key, decode_rate, merged)


def fmt_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
