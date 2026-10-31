"""标题字体目录：自动识别本机字体 + 推荐可下载字体。

往项目根目录的 fonts/ 文件夹里放入 .ttf / .otf / .ttc 后即可在界面中选择。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 打包成 exe 后，字体目录放在 exe 旁边（保证可写）
if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent.parent
USER_FONT_DIR = ROOT / "fonts"
WINDOWS_FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"

CATEGORIES = (
    "文艺 · 古典",
    "现代 · 极简",
    "日系 · 和风",
    "标题 · 海报",
    "手写 · 温度",
    "复古 · 胶片",
)


def _entry(
    key: str,
    name: str,
    category: str,
    vibe: str,
    candidates: list,
    sample: str,
    license_: str = "系统字体",
    url: str = "",
    keywords: tuple[str, ...] = (),
) -> dict:
    return {
        "key": key,
        "name": name,
        "category": category,
        "vibe": vibe,
        "candidates": candidates,
        "sample": sample,
        "license": license_,
        "url": url,
        "keywords": keywords,
    }


CATALOG: list[dict] = [
    _entry(
        "noto-serif", "思源宋体", "文艺 · 古典",
        "文艺片 / 时代剧 / 片尾字幕，最接近日式电影海报的气质",
        [("NotoSerifSC-VF.ttf", 0), ("SourceHanSerifSC-Regular.otf", 0),
         ("SourceHanSerifSC-VF.otf", 0), ("NotoSerifSC-Regular.otf", 0)],
        "君の名は。", "SIL OFL 1.1 开源",
        "https://fonts.google.com/noto/specimen/Noto+Serif+SC",
        ("sourcehan", "思源宋"),
    ),
    _entry(
        "stzhongs", "华文中宋", "文艺 · 古典",
        "厚重、有年代感的正片标题",
        [("STZHONGS.TTF", 0)], "山河故人",
    ),
    _entry(
        "simli", "隶书", "文艺 · 古典",
        "历史纪录片 / 古装 / 史诗",
        [("SIMLI.TTF", 0)], "大秦帝国",
    ),
    _entry(
        "stxingka", "华文行楷", "文艺 · 古典",
        "武侠 / 古装 / 江湖气",
        [("STXINGKA.TTF", 0)], "笑傲江湖",
    ),
    _entry(
        "noto-sans", "思源黑体", "现代 · 极简",
        "干净、克制，适合当代都市与悬疑片",
        [("NotoSansSC-VF.ttf", 0), ("SourceHanSansSC-Regular.otf", 0),
         ("NotoSansSC-Regular.otf", 0)],
        "无声告白", "SIL OFL 1.1 开源",
        "https://fonts.google.com/noto/specimen/Noto+Sans+SC",
        ("sourcehan", "思源黑"),
    ),
    _entry(
        "msyh", "微软雅黑", "现代 · 极简",
        "通用型 UI 气质，适合现代题材",
        [("msyh.ttc", 0)], "日常",
    ),
    _entry(
        "msyh-light", "微软雅黑 Light", "现代 · 极简",
        "细笔画，轻盈、干净的极简海报",
        [("msyhl.ttc", 0)], "步履不停",
    ),
    _entry(
        "deng", "等线", "现代 · 极简",
        "细而均匀，适合冷峻、理性的影像",
        [("Deng.ttf", 0)], "第三度嫌疑人",
    ),
    _entry(
        "stxihei", "华文细黑", "现代 · 极简",
        "细黑体，常见于电影片名",
        [("STXIHEI.TTF", 0)], "一一",
    ),
    _entry(
        "simyou", "幼圆", "现代 · 极简",
        "圆润亲和，适合治愈系与日常番",
        [("SIMYOU.TTF", 0)], "我和你的光年距离",
    ),
    _entry(
        "yugothic-light", "悠黑 Light", "日系 · 和风",
        "日系极简、干净留白",
        [("YuGothL.ttc", 0)], "君の名は。",
    ),
    _entry(
        "yugothic", "悠黑", "日系 · 和风",
        "日式现代片名常用",
        [("YuGothR.ttc", 0), ("YuGothM.ttc", 0)], "天気の子",
    ),
    _entry(
        "msgothic", "MS Gothic", "日系 · 和风",
        "九十年代日式动画 / 像素感",
        [("msgothic.ttc", 0)], "攻殻機動隊",
    ),
    _entry(
        "sourcehan-jp", "思源黑体 JP", "日系 · 和风",
        "日文字形，适合日本动画标题",
        [("SourceHanSansJP-Normal.otf", 0), ("SourceHanSansJP-Bold.otf", 0)],
        "君の名は。", "SIL OFL 1.1 开源",
        "https://github.com/adobe-fonts/source-han-sans/releases",
        ("sourcehanjp", "思源黑jp"),
    ),
    _entry(
        "simhei", "黑体", "标题 · 海报",
        "强硬、粗粝，适合机甲 / 动作 / 犯罪",
        [("simhei.ttf", 0)], "暴裂无声",
    ),
    _entry(
        "sthupo", "华文琥珀", "标题 · 海报",
        "圆胖厚重，港片喜剧片头感",
        [("STHUPO.TTF", 0)], "功夫",
    ),
    _entry(
        "stcaiyun", "华文彩云", "标题 · 海报",
        "内部镂空，适合奇幻 / 特效片",
        [("STCAIYUN.TTF", 0)], "捉妖记",
    ),
    _entry(
        "fzyaoti", "方正姚体", "标题 · 海报",
        "修长挺拔，适合文艺片海报",
        [("FZYTK.TTF", 0)], "推拿",
    ),
    _entry(
        "smiley-sans", "得意黑", "标题 · 海报",
        "倾斜潮流感，适合青春 / 番剧 / 音乐",
        [("SmileySans-Oblique.ttf", 0), ("SmileySans.ttf", 0)],
        "灌篮高手", "SIL OFL 1.1 开源",
        "https://github.com/atelier-anchor/smiley-sans/releases",
        ("smiley", "得意黑"),
    ),
    _entry(
        "zcool-gaoduanhei", "站酷高端黑", "标题 · 海报",
        "综艺 / 商业大片标题",
        [("ZCOOLGaoDuanHei.ttf", 0), ("站酷高端黑.ttf", 0)],
        "流浪地球", "免费商用（以站酷官方为准）",
        "https://www.zcool.com.cn/special/zcoolfonts/",
        ("zcool", "站酷"),
    ),
    _entry(
        "simkai", "楷体", "手写 · 温度",
        "书信、回忆、温情段落",
        [("simkai.ttf", 0)], "情书",
    ),
    _entry(
        "stkaiti", "华文楷体", "手写 · 温度",
        "清秀手写，适合治愈系动画",
        [("STKAITI.TTF", 0)], "言叶之庭",
    ),
    _entry(
        "fzshuti", "方正舒体", "手写 · 温度",
        "随手写下的标题感",
        [("FZSTK.TTF", 0)], "你好，李焕英",
    ),
    _entry(
        "lxgw-wenkai", "霞鹜文楷", "手写 · 温度",
        "温暖手写楷书，番剧片名神器",
        [("LXGWWenKai-Regular.ttf", 0), ("LXGWWenKai.ttf", 0)],
        "夏目友人帐", "SIL OFL 1.1 开源",
        "https://github.com/lxgw/LxgwWenKai/releases",
        ("lxgw", "wenkai", "霞鹜"),
    ),
    _entry(
        "simsun", "宋体", "复古 · 胶片",
        "旧字幕 / 铅字印刷 / 怀旧质感",
        [("simsun.ttc", 0)], "牯岭街少年杀人事件",
    ),
    _entry(
        "simfang", "仿宋", "复古 · 胶片",
        "民国文献 / 纪录片解说字幕",
        [("simfang.ttf", 0)], "我在故宫修文物",
    ),
    # —— 日文原版 ——
    # —— Windows 中文系统字体 ——
    _entry(
        "stliti", "华文隶书", "文艺 · 古典",
        "汉代隶意，适合古装、史诗、历史纪录片",
        [("STLITI.TTF", 0)], "赤壁",
    ),
    _entry(
        "stxinwei", "华文新魏", "标题 · 海报",
        "魏碑笔意，硬朗有筋骨，适合武侠与战争片",
        [("STXINWEI.TTF", 0)], "三国之见龙卸甲",
    ),
    _entry(
        "stsong", "华文宋体", "文艺 · 古典",
        "端正的印刷宋体，适合正剧与纪录电影",
        [("STSONG.TTF", 0)], "那山那人那狗",
    ),
    _entry(
        "stfangso", "华文仿宋", "复古 · 胶片",
        "旧公文与老字幕的笔画，年代感强",
        [("STFANGSO.TTF", 0)], "城南旧事",
    ),
    # —— Windows 中文系统字体 ——
    _entry(
        "harmony-sans", "HarmonyOS Sans", "现代 · 极简",
        "几何现代黑体，界面感强，适合科幻与都市",
        [("HarmonyOS_Sans_SC_Regular.ttf", 0), ("HarmonyOS_Sans_SC.ttf", 0)],
        "流浪地球", "免费商用（华为）",
        "https://developer.harmonyos.com/cn/docs/design/des-guides/font-0000001157868583",
        ("harmonyos", "鸿蒙"),
    ),
    _entry(
        "alibaba-puhuiti", "阿里巴巴普惠体", "现代 · 极简",
        "通用商用黑体，字面开阔，适合商业片标题",
        [("AlibabaPuHuiTi-3-55-Regular.ttf", 0),
         ("AlibabaPuHuiTi-2-55-Regular.ttf", 0),
         ("AlibabaPuHuiTi-Regular.otf", 0)],
        "我和我的祖国", "免费商用（阿里）",
        "https://www.alibabafonts.com/", ("alibaba", "普惠", "puhui"),
    ),
    _entry(
        "oppo-sans", "OPPO Sans", "现代 · 极简",
        "轻快现代黑体，适合青春、校园、都市题材",
        [("OPPOSans-M.ttf", 0), ("OPPOSans-R.ttf", 0), ("OPPO-Sans.ttf", 0)],
        "风犬少年的天空", "免费商用（OPPO）",
        "https://www.coloros.com/oppo-sans/", ("opposans", "oppo"),
    ),
    _entry(
        "zcool-qingke-huangyou", "站酷庆科黄油体", "标题 · 海报",
        "圆润厚重的综艺感标题，适合喜剧与合家欢",
        [("ZCOOLQingKeHuangYou-Regular.ttf", 0), ("站酷庆科黄油体.ttf", 0)],
        "大圣归来", "免费商用（以站酷官方为准）",
        "https://fonts.google.com/specimen/ZCOOL+QingKe+HuangYou",
        ("qingke", "黄油"),
    ),
    _entry(
        "zcool-kuaile", "站酷快乐体", "标题 · 海报",
        "手绘感粗体，动画电影与儿童题材首选",
        [("ZCOOLKuaiLe-Regular.ttf", 0), ("站酷快乐体.ttf", 0)],
        "哪吒之魔童降世", "免费商用（以站酷官方为准）",
        "https://fonts.google.com/specimen/ZCOOL+KuaiLe", ("kuaile", "快乐"),
    ),
    _entry(
        "zcool-xiaowei", "站酷小薇LOHO体", "手写 · 温度",
        "清秀的手写宋，适合治愈系与日常番",
        [("ZCOOLXiaoWei-Regular.ttf", 0), ("站酷小薇.ttf", 0)],
        "快把我哥带走", "免费商用（以站酷官方为准）",
        "https://fonts.google.com/specimen/ZCOOL+XiaoWei", ("xiaowei", "小薇"),
    ),
    _entry(
        "long-cang", "龙藏体", "手写 · 温度",
        "瘦长的行书，奇幻与古风片名很出彩",
        [("LongCang-Regular.ttf", 0), ("龙藏体.ttf", 0)],
        "大鱼海棠", "SIL OFL 1.1 开源",
        "https://fonts.google.com/specimen/Long+Cang", ("longcang", "龙藏"),
    ),
    _entry(
        "ma-shan-zheng", "马善政毛笔楷书", "手写 · 温度",
        "毛笔楷书，武侠与水墨动画的落款感",
        [("MaShanZheng-Regular.ttf", 0)], "影", "SIL OFL 1.1 开源",
        "https://fonts.google.com/specimen/Ma+Shan+Zheng",
        ("mashanzheng", "马善政"),
    ),
    _entry(
        "zhi-mang-xing", "志莽行书", "手写 · 温度",
        "飞扬的行书，适合侠气与爱情片片头",
        [("ZhiMangXing-Regular.ttf", 0)], "刺客聂隐娘", "SIL OFL 1.1 开源",
        "https://fonts.google.com/specimen/Zhi+Mang+Xing",
        ("zhimangxing", "志莽"),
    ),
    _entry(
        "liu-jian-mao-cao", "柳建毛草", "手写 · 温度",
        "狂草笔触，适合东方奇幻与水墨海报",
        [("LiuJianMaoCao-Regular.ttf", 0)], "妖猫传", "SIL OFL 1.1 开源",
        "https://fonts.google.com/specimen/Liu+Jian+Mao+Cao",
        ("liujian", "毛草"),
    ),
    _entry(
        "youshe-title", "优设标题黑", "标题 · 海报",
        "倾斜厚重的标题黑，综艺与短视频封面常用",
        [("YouSheBiaoTiHei.ttf", 0), ("优设标题黑.ttf", 0)],
        "我和我的家乡", "免费商用（优设）",
        "https://www.uisdc.com/uisdc-font", ("youshe", "优设"),
    ),
]


def _user_font_files() -> list[Path]:
    if not USER_FONT_DIR.is_dir():
        return []
    suffixes = {".ttf", ".otf", ".ttc", ".otc"}
    return [p for p in USER_FONT_DIR.iterdir() if p.suffix.lower() in suffixes]


def _locate(entry: dict, user_files: list[Path]) -> tuple[Path, int] | None:
    for name, index in entry["candidates"]:
        for base in (USER_FONT_DIR, WINDOWS_FONT_DIR):
            candidate = base / name
            try:
                if candidate.is_file():
                    return candidate, index
            except OSError:
                continue
    joined = " ".join(entry["keywords"]).lower()
    if joined:
        for path in user_files:
            name = path.name.lower()
            if any(k.lower() in name for k in entry["keywords"]):
                return path, 0
    return None


def list_fonts() -> list[dict]:
    user_files = _user_font_files()
    result = []
    for entry in CATALOG:
        found = _locate(entry, user_files)
        result.append(
            {
                "key": entry["key"],
                "name": entry["name"],
                "category": entry["category"],
                "vibe": entry["vibe"],
                "license": entry["license"],
                "url": entry["url"],
                "sample": entry["sample"],
                "available": found is not None,
                "path": str(found[0]) if found else "",
                "index": found[1] if found else 0,
            }
        )
    return result


def resolve_font(key: str) -> tuple[str, int]:
    """返回 (字体文件路径, ttc 索引)。找不到时回退到第一个可用中文字体。"""
    user_files = _user_font_files()
    for entry in CATALOG:
        if entry["key"] == key:
            found = _locate(entry, user_files)
            if found:
                return str(found[0]), found[1]
            break
    for preferred in (
        "noto-serif",
        "noto-sans",
        "stzhongs",
        "msyh",
        "simhei",
        "simsun",
    ):
        for entry in CATALOG:
            if entry["key"] == preferred:
                found = _locate(entry, user_files)
                if found:
                    return str(found[0]), found[1]
    return "", 0
