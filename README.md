# anime impression — 色带生成器

把电影 / 番剧的整条时间轴压缩成一张「色带海报」：逐帧提取画面主色调，按横向、纵向、斜向、同心圆、螺旋等排列方式渲染成图，再叠加片名、噪点与虚化，得到一张属于你自己的观影纪念海报。

<img width="2560" height="720" alt="败犬女主太多了！-2560x720 (4)" src="https://github.com/user-attachments/assets/8ad3fa86-2e51-45eb-81ad-743376e4683a" />
<img width="2560" height="720" alt="败犬女主太多了！-2560x720" src="https://github.com/user-attachments/assets/8871a4e5-62a1-4c71-997a-27ff7fc2d723" />
<img width="2560" height="720" alt="败犬女主太多了！-2560x720 (1)" src="https://github.com/user-attachments/assets/0c1244b2-94bb-47e5-840d-650f7bcb1ab2" />
<img width="2560" height="720" alt="败犬女主太多了！-2560x720 (2)" src="https://github.com/user-attachments/assets/3a17c28a-0b55-463d-b56c-e88749437b13" />
<img width="2539" height="1341" alt="image" src="https://github.com/user-attachments/assets/9758dd0c-27f8-43cf-9204-08f4f13f0095" />

## 功能特性

- **多视频合成**：把多部影片（或同一部的多集）按顺序合成一条时间轴采样，支持拖动排序
- **五种排列**：横向 / 纵向 / 斜向 / 同心圆 / 螺旋
- **采样调节**：色带间隔（采样频率）、色带宽度、画布分辨率
- **片头片尾跳过**：每个视频可单独或批量设置跳过前后 n 分钟，避开 OP / ED 色带重复
- **黑边检测**：自动裁掉 letterbox 黑边，颜色更纯净
- **后处理**：标题文字（位置、大小、颜色）、胶片噪点、背景虚化
- **41 款精选字体**：内置字体目录，自动识别本机字体；`fonts/` 文件夹放入任意 `.ttf / .otf / .ttc` 即可在界面中选用
- **实时预览**：生成过程中色带逐条出现，参数调整即时重渲染

## 性能设计

- **切片并行解码**：长视频按 3 分钟切片，多进程并行解码后按时间线顺序合并
- **智能跳帧**：解码层跳过非参考 B 帧，平均色采样下画质无损、速度翻倍
- **硬件解码**：HEVC 自动启用 GPU 解码，失败自动回退软件解码并记住结果
- **三层缓存**：黑边检测结果、密集采样结果（2 条/秒）落盘缓存；**换排列方式、调间隔、改色带宽度等所有参数调整都无需重新解码**，毫秒级重采样出图
- 只有首次解析某个视频需要完整解码，之后同素材的任何调整都是秒出

## 快速开始

### 方式一：下载打包版（Windows，推荐）

从 [Releases](../../releases) 下载 `anime_impression-win64.zip`，解压后双击 `anime_impression.exe`，浏览器自动打开 `http://127.0.0.1:8787`。

无需安装 Python 和 ffmpeg，字体已内置 12 款，可自行往 exe 旁的 `fonts/` 文件夹补充。

### 方式二：源码运行

依赖：Python 3.10+（ffmpeg 由 imageio-ffmpeg 自动提供）

```bash
pip install -r requirements.txt
python run.py            # 启动并自动打开浏览器
# 或
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
```

## 使用说明

1. 左侧「选择视频」添加一个或多个视频文件，拖动卡片调整顺序
2. 调节采样间隔、色带宽度、排列方式与画布分辨率
3. 需要避开 OP/ED 时，设置片头/片尾跳过（可批量应用到全部影片）
4. 点击生成，右侧预览区色带逐条出现
5. 后处理区调整标题字体、位置、噪点、虚化，满意后导出 PNG

## 项目结构

```
├── run.py              # 启动入口（打包 + 开发共用，--dialog 为文件选择模式）
├── app/
│   ├── main.py         # FastAPI 服务：作业调度 / 渲染 / 缓存
│   ├── video.py        # ffmpeg 采样：切片并行 / 跳帧 / 硬解 / 三层缓存
│   ├── plan.py         # 色带分配计划（各排列方式的容量计算）
│   ├── layout.py       # 色带几何布局
│   ├── render.py       # 海报渲染（底图缓存 / 噪点 / 虚化）
│   ├── fonts.py        # 41 款字体目录与本机字体识别
│   └── dialog.py       # 原生文件选择框（独立进程，不阻塞服务）
├── static/             # 前端（原生 HTML/CSS/JS，无构建）
└── fonts/              # 用户字体目录，放入字体文件即可被识别
```

## 打包

```bash
pip install pyinstaller
python -m PyInstaller anime_impression.spec
# 产物在 dist/anime_impression/，与 fonts/ 一起分发
```

## 字体版权说明

目录中「系统字体」条目依赖本机已安装字体（Windows 自带）；开源字体（思源系列、得意黑、霞鹜文楷等）遵循各自的开源协议，商用前请查阅对应授权条款。个别未随包分发的系统专有字体（MS Mincho、Meiryo 等）需自行安装对应语言包。

## 许可证

本项目代码采用 [MIT License](LICENSE)。
