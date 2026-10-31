"""FastAPI 服务：探测 / 计划 / 提取作业 / 渲染 / 字体。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import fonts, layout, plan as plan_mod, render, video

# 打包成 exe 后：只读资源（static）在解包目录，可写目录在 exe 旁边
if getattr(sys, "frozen", False):
    ASSET_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    ROOT = Path(sys.executable).resolve().parent
else:
    ASSET_DIR = ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ASSET_DIR / "static"
DIALOG_SCRIPT = Path(__file__).resolve().parent / "dialog.py"

app = FastAPI(title="anime impression", docs_url=None, redoc_url=None)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

JOBS: dict[str, "Job"] = {}
JOBS_LOCK = threading.Lock()
RENDER_LOCK = threading.Lock()
RENDER_CACHE: OrderedDict[str, bytes] = OrderedDict()
# 不含后处理的底图缓存：只改标题/噪点/虚化时无需重画整张色带
BASE_CACHE: OrderedDict[str, Any] = OrderedDict()
FONT_PREVIEW_CACHE: OrderedDict[str, bytes] = OrderedDict()


class Job:
    def __init__(self, job_id: str, plan_data: dict[str, Any]):
        self.id = job_id
        self.plan = plan_data
        self.lock = threading.Lock()
        self.bands: list[str] = []
        self.status = "running"
        self.message = "准备中"
        self.error = ""
        self.cancel = threading.Event()
        self.started = time.time()
        self._colors: np.ndarray | None = None
        self._colors_count = -1
        self.video_states = [
            {
                "name": v["name"],
                "status": "waiting",
                "planned": v["bands"],
                "done": 0,
            }
            for v in plan_data["perVideo"]
        ]

    def add_bands(self, colors: list[str]) -> None:
        with self.lock:
            self.bands.extend(colors)

    def set_video_state(self, index: int, status: str) -> None:
        with self.lock:
            if 0 <= index < len(self.video_states):
                self.video_states[index]["status"] = status

    def colors(self) -> np.ndarray:
        with self.lock:
            count = len(self.bands)
            if self._colors_count == count and self._colors is not None:
                return self._colors
            hexes = list(self.bands)
        arr = layout.hex_to_rgb(hexes)
        with self.lock:
            self._colors = arr
            self._colors_count = count
        return arr

    def snapshot(self, since: int) -> dict[str, Any]:
        with self.lock:
            total = len(self.bands)
            delta = self.bands[since : since + 400]
            next_since = since + len(delta)
            states = [dict(s) for s in self.video_states]
            status = self.status
            message = self.message
            error = self.error
            elapsed = round(time.time() - self.started, 1)
        planned = max(1, self.plan["bands"])
        return {
            "id": self.id,
            "status": status,
            "total": total,
            "bands": delta,
            "nextSince": next_since,
            "planned": self.plan["bands"],
            "progress": min(1.0, total / planned),
            "message": message,
            "error": error,
            "videos": states,
            "elapsed": elapsed,
        }


def _probe_all(paths: list[str]) -> list[dict[str, Any]]:
    result = []
    for path in paths:
        info = video.probe_video(path)
        result.append(
            {
                "path": info.path,
                "name": info.name,
                "duration": round(info.duration, 3),
                "durationText": video.fmt_duration(info.duration),
                "width": info.width,
                "height": info.height,
                "fps": info.fps,
                "size": info.size,
            }
        )
    return result


def _build_plan_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_videos = payload.get("videos") or []
    if not raw_videos:
        raise HTTPException(status_code=400, detail="请先选择至少一个视频")
    videos = []
    for item in raw_videos:
        path = item.get("path")
        if not path:
            continue
        info = video.probe_video(path)
        videos.append(
            {
                "path": info.path,
                "name": info.name,
                "duration": info.duration,
                "skipStart": float(item.get("skipStart", 0) or 0),
                "skipEnd": float(item.get("skipEnd", 0) or 0),
            }
        )
    if not videos:
        raise HTTPException(status_code=400, detail="没有有效的视频文件")
    return plan_mod.build_plan(videos, payload.get("options") or {})


def _run_job(job: Job) -> None:
    try:
        for index, item in enumerate(job.plan["perVideo"]):
            if job.cancel.is_set():
                break
            if item["trimmed"] < 1.0 or item["bands"] <= 0:
                job.set_video_state(index, "skipped")
                continue

            job.set_video_state(index, "running")
            job.message = f"正在解析 {item['name']}"
            info = video.probe_video(item["path"])
            crop = None
            if job.plan["options"].get("autoCrop", True):
                job.message = f"正在检测黑边 · {item['name']}"
                crop = video.detect_crop(info)
            job.message = f"正在解析 {item['name']}"
            video.extract_video(
                info,
                item["start"],
                item["trimmed"],
                item["bands"],
                job.add_bands,
                job.cancel,
                crop,
            )
            if job.cancel.is_set():
                break
            job.set_video_state(index, "done")

        if job.cancel.is_set():
            job.status = "cancelled"
            job.message = "已取消"
        else:
            job.status = "done"
            job.message = "完成"
    except Exception as exc:  # noqa: BLE001
        job.status = "error"
        job.error = str(exc)
        job.message = "解析失败"


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "ffmpeg": video.FFMPEG if os.path.isfile(video.FFMPEG) else "",
        "cpu": os.cpu_count(),
        "fontsDir": str(fonts.USER_FONT_DIR),
        "windowsFonts": os.path.isdir(fonts.WINDOWS_FONT_DIR),
    }


@app.post("/api/probe")
def api_probe(payload: dict[str, Any]) -> dict[str, Any]:
    paths = [str(p) for p in (payload.get("paths") or [])]
    if not paths:
        raise HTTPException(status_code=400, detail="缺少视频路径")
    infos, errors = [], []
    for path in paths:
        try:
            infos.extend(_probe_all([path]))
        except Exception as exc:  # noqa: BLE001
            errors.append({"path": path, "error": str(exc)})
    return {"videos": infos, "errors": errors}


@app.post("/api/dialog")
def api_dialog() -> dict[str, Any]:
    # 打包后没有独立 python，让 exe 以 --dialog 模式自唤起
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--dialog"]
    else:
        cmd = [sys.executable, str(DIALOG_SCRIPT)]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            env=env,
            timeout=300,
            creationflags=flags,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="文件选择框超时") from exc

    raw = (proc.stdout or "").strip()
    # 控制台日志：子进程究竟返回了什么（取消 / 出错 / 被拦截），一目了然
    print(
        f"[dialog] code={proc.returncode} "
        f"out={raw[:200]!r} err={(proc.stderr or '').strip()[-200:]!r}"
    )
    if not raw:
        # 子进程没有任何输出：多半是被杀软拦截或启动即崩溃，把线索带给前端
        err = (proc.stderr or "").strip()
        tail = err[-300:] if err else ""
        return {
            "paths": [],
            "canceled": True,
            "error": (
                tail
                if tail
                else f"文件选择器未返回结果（退出码 {proc.returncode}），"
                "请确认未被杀毒软件拦截"
            ),
        }
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"paths": [], "canceled": True, "error": "文件选择器输出异常"}
    if isinstance(data, dict) and data.get("error"):
        return {"paths": [], "canceled": True, "error": str(data["error"])}
    if not isinstance(data, list):
        return {"paths": [], "canceled": True}
    return {"paths": [p for p in data if os.path.isfile(p)], "canceled": not data}


@app.post("/api/plan")
def api_plan(payload: dict[str, Any]) -> dict[str, Any]:
    return _build_plan_from_payload(payload)


@app.post("/api/jobs")
def api_create_job(payload: dict[str, Any]) -> dict[str, Any]:
    plan_data = _build_plan_from_payload(payload)
    if plan_data["bands"] <= 0:
        raise HTTPException(status_code=400, detail="可采样时长不足，无法生成色带")

    job_id = uuid.uuid4().hex[:12]
    job = Job(job_id, plan_data)
    with JOBS_LOCK:
        JOBS[job_id] = job
        finished = [j for j in JOBS.values() if j.status != "running"]
        for stale in finished[:-6]:
            JOBS.pop(stale.id, None)

    threading.Thread(target=_run_job, args=(job,), daemon=True).start()
    return {"jobId": job_id, "plan": plan_data}


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str, since: int = 0) -> dict[str, Any]:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在或已过期")
    return job.snapshot(max(0, since))


@app.delete("/api/jobs/{job_id}")
def api_cancel_job(job_id: str) -> dict[str, Any]:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    job.cancel.set()
    return {"ok": True}


@app.post("/api/render")
def api_render(payload: dict[str, Any]) -> Response:
    job_id = payload.get("jobId")
    job = JOBS.get(str(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    colors = job.colors()
    if len(colors) == 0:
        raise HTTPException(status_code=400, detail="还没有生成任何色带")

    options = plan_mod.normalize_options(payload.get("options") or {})
    post = render.normalize_post(payload.get("post") or {})
    try:
        scale = float(payload.get("scale", 1.0))
    except (TypeError, ValueError):
        scale = 1.0
    scale = max(0.05, min(1.0, scale))

    key_src = json.dumps(
        {
            "job": job_id,
            "n": int(len(colors)),
            "options": options,
            "post": post,
            "scale": round(scale, 4),
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    key = hashlib.md5(key_src.encode("utf-8")).hexdigest()
    base_key = hashlib.md5(
        json.dumps(
            {"job": job_id, "n": int(len(colors)), "options": options, "scale": round(scale, 4)},
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    download = bool(payload.get("download"))

    with RENDER_LOCK:
        cached = RENDER_CACHE.get(key)
        if cached is not None:
            RENDER_CACHE.move_to_end(key)
            data = cached
        else:
            base = BASE_CACHE.get(base_key)
            if base is not None:
                BASE_CACHE.move_to_end(base_key)
            else:
                base = render.build_base(colors, options, scale)
                BASE_CACHE[base_key] = base
                while len(BASE_CACHE) > 4:
                    BASE_CACHE.popitem(last=False)
            # 预览图用低压缩等级（编码快数倍），导出才用高质量压缩
            data = render.render_png(
                colors,
                options,
                post,
                scale,
                base=base,
                compress_level=6 if download else 1,
            )
            RENDER_CACHE[key] = data
            while len(RENDER_CACHE) > 6:
                RENDER_CACHE.popitem(last=False)

    headers = {"Cache-Control": "no-store"}
    if payload.get("download"):
        headers["Content-Disposition"] = 'attachment; filename="anime-impression.png"'
    return Response(content=data, media_type="image/png", headers=headers)


@app.get("/api/fonts")
def api_fonts() -> dict[str, Any]:
    return {"categories": list(fonts.CATEGORIES), "fonts": fonts.list_fonts()}


@app.get("/api/fonts/preview")
def api_font_preview(
    key: str, text: str = "", size: int = 76
) -> Response:
    cache_key = f"{key}|{text}|{size}"
    with RENDER_LOCK:
        cached = FONT_PREVIEW_CACHE.get(cache_key)
        if cached is not None:
            FONT_PREVIEW_CACHE.move_to_end(cache_key)
            return Response(
                content=cached,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=3600"},
            )
    data = render.font_preview_png(key, text, size)
    with RENDER_LOCK:
        FONT_PREVIEW_CACHE[cache_key] = data
        while len(FONT_PREVIEW_CACHE) > 64:
            FONT_PREVIEW_CACHE.popitem(last=False)
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/")
def index() -> FileResponse:
    if not (STATIC_DIR / "index.html").is_file():
        raise HTTPException(status_code=500, detail="前端文件缺失")
    return FileResponse(
        STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"}
    )


@app.exception_handler(404)
async def not_found(request: Request, exc: Any) -> JSONResponse:
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "接口不存在"})
    return JSONResponse(status_code=404, content={"detail": "页面不存在"})
