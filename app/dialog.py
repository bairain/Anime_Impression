"""原生文件选择对话框（在独立进程中运行，避免阻塞 Web 服务）。

任何异常都以 JSON 形式打到 stdout，让主进程能向界面展示真实原因，
而不是静默返回空列表（表现为"无法导入视频"却毫无提示）。
"""
from __future__ import annotations

import json


def main() -> None:
    try:
        paths = _pick()
        # ensure_ascii=True：输出纯 ASCII（\uXXXX 转义），
        # 不依赖子进程 stdout 的实际编码，杜绝中文路径乱码
        print(json.dumps(list(paths), ensure_ascii=True))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=True))


def _pick() -> tuple[str, ...]:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    root.update()

    try:
        paths = filedialog.askopenfilenames(
            parent=root,
            title="选择视频文件",
            filetypes=[
                (
                    "视频文件",
                    "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.ts *.m2ts "
                    "*.rmvb *.rm *.mpg *.mpeg *.m4v *.3gp *.ogv *.vob",
                ),
                ("所有文件", "*.*"),
            ],
        )
    finally:
        root.destroy()
    return tuple(paths)


if __name__ == "__main__":
    main()
