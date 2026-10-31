"""anime impression 启动入口（同时用于 PyInstaller 打包）。

- `anime_impression.exe`          启动 Web 服务并自动打开浏览器
- `anime_impression.exe --dialog` 内部使用：弹出文件选择框（JSON 输出到 stdout）
"""
from __future__ import annotations

import sys
import threading
import time
import webbrowser

URL = "http://127.0.0.1:8787"


def main() -> None:
    if "--dialog" in sys.argv:
        from app.dialog import main as dialog_main

        dialog_main()
        return

    import uvicorn

    from app.main import app

    def open_browser() -> None:
        time.sleep(1.2)
        try:
            webbrowser.open(URL)
        except Exception:  # noqa: BLE001
            pass

    threading.Thread(target=open_browser, daemon=True).start()
    print(f"anime impression 已启动：{URL}（关闭本窗口即退出）")
    uvicorn.run(app, host="127.0.0.1", port=8787, log_level="info")


if __name__ == "__main__":
    main()
