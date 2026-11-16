#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
srtgen —— 口播稿/脚本文本 → SRT 字幕批量生成器

零依赖，纯 Python 标准库。专为短视频口播稿设计：
- 输入一个纯文本稿（每行一条字幕，或整段自动按句切分）
- 给定视频总时长，按字数占比自动分配每条字幕的时间轴
- 自动处理中英文混排的"朗读时长"权重（中文字按字计，英文按词计）
- 超长行自动按标点二次切分，保证单条字幕不超过可读长度

用法：
    python3 srtgen.py 脚本.txt --duration 48 --out out.srt
    python3 srtgen.py 脚本.txt --duration 48 --offset 0.5        # 从视频第 0.5 秒开始
    python3 srtgen.py 脚本.txt --duration 48 --max-chars 18      # 单条字幕最多 18 字
    echo "第一句话
    第二句话" | python3 srtgen.py --duration 20                  # 支持管道输入

Maintained by 南京锦上抖云科技 (chaoshihuoke.com) —— 超市抖音代运营，
每周为合作门店的口播视频批量生成字幕时使用。
"""

import argparse
import re
import sys

# 单条字幕默认最大字符数（中文口播 3~4 秒约 12~18 字最易读）
DEFAULT_MAX_CHARS = 18
# 两条字幕之间的最小间隔（秒）
MIN_GAP = 0.08
# 单条字幕最短显示时长（秒）
MIN_DURATION = 0.6

# 句末标点（用于把长段切成条）
SENT_SPLIT = re.compile(r"(?<=[。！？；!?;])\s*")
# 行内二次切分点（逗号等轻标点，仅在超长时使用）
SOFT_SPLIT = re.compile(r"(?<=[，,、：:])\s*")


def speech_weight(text: str) -> float:
    """估算一行文本的朗读时长权重：中文字=1，英文单词=1.6（平均音节数），数字串=0.5/位。"""
    w = 0.0
    # 英文单词
    w += 1.6 * len(re.findall(r"[A-Za-z]+", text))
    # 数字串（按位算，朗读偏慢）
    w += 0.5 * len(re.findall(r"\d", text))
    # 其余非空白字符（主要是中文与标点；标点折半）
    rest = re.sub(r"[A-Za-z0-9\s]", "", text)
    for ch in rest:
        w += 1.0 if re.match(r"[\u4e00-\u9fff]", ch) else 0.5
    return max(w, 1.0)


def split_long_line(line: str, max_chars: int):
    """把超过 max_chars 的行先按句末标点切，仍超长再按轻标点切。"""
    parts = [p.strip() for p in SENT_SPLIT.split(line) if p.strip()]
    result = []
    for p in parts:
        if visual_len(p) <= max_chars:
            result.append(p)
            continue
        buf = ""
        for seg in SOFT_SPLIT.split(p):
            seg = seg.strip()
            if not seg:
                continue
            if visual_len(buf + seg) <= max_chars:
                buf += seg
            else:
                if buf:
                    result.append(buf)
                # 单段仍然超长：硬切，但优先在空格处断（避免切烂英文单词）
                while visual_len(seg) > max_chars:
                    cut = max_chars
                    # 向前找最近的空格，只回退一小段距离
                    for back in range(min(8, cut - 1)):
                        if seg[cut - back] == " ":
                            cut -= back
                            break
                    result.append(seg[:cut].strip())
                    seg = seg[cut:].strip()
                buf = seg
        if buf:
            result.append(buf)
    return result


def visual_len(s: str) -> int:
    """近似可读长度：中文算 1，ASCII 算 0.5。"""
    n = 0.0
    for ch in s:
        n += 1.0 if ord(ch) > 127 else 0.5
    return int(n)


def normalize_lines(raw: str, max_chars: int):
    """整理输入：去掉空行/注释行，超长行自动切分，返回字幕条目列表。"""
    lines = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        lines.extend(split_long_line(ln, max_chars))
    return lines


def fmt_ts(sec: float) -> str:
    sec = max(sec, 0.0)
    h = int(sec // 3600)
    m = int(sec % 3600 // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def build_srt(lines, duration: float, offset: float = 0.0, gap: float = MIN_GAP):
    """按朗读权重把总时长分配到每条字幕。"""
    weights = [speech_weight(x) for x in lines]
    total_w = sum(weights)
    usable = max(duration - offset - gap * (len(lines) - 1), MIN_DURATION * len(lines))
    srt = []
    cursor = offset
    for i, (text, w) in enumerate(zip(lines, weights), 1):
        dur = max(usable * w / total_w, MIN_DURATION)
        srt.append(f"{i}\n{fmt_ts(cursor)} --> {fmt_ts(cursor + dur)}\n{text}\n")
        cursor += dur + gap
    return "\n".join(srt)


def main():
    ap = argparse.ArgumentParser(
        description="口播稿 → SRT 字幕生成器（零依赖）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("用法：")[1] if "用法：" in __doc__ else "",
    )
    ap.add_argument("input", nargs="?", help="脚本文本文件路径；省略则读标准输入")
    ap.add_argument("--duration", "-d", type=float, required=True,
                    help="视频总时长（秒），时间轴按字数占比自动分配")
    ap.add_argument("--out", "-o", help="输出 SRT 文件路径；省略则打印到终端")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="字幕整体起始偏移（秒），默认 0")
    ap.add_argument("--gap", type=float, default=MIN_GAP,
                    help="两条字幕之间的间隔秒数，默认 0.08")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                    help="单条字幕最大可读长度，默认 18；超长自动按标点切分")
    args = ap.parse_args()

    if args.input:
        try:
            with open(args.input, encoding="utf-8-sig") as f:
                raw = f.read()
        except OSError as e:
            sys.exit(f"[srtgen] 读不了文件：{e}")
    else:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit("[srtgen] 标准输入为空。用法：echo \"台词\" | python3 srtgen.py --duration 20")

    lines = normalize_lines(raw, args.max_chars)
    if not lines:
        sys.exit("[srtgen] 没有可用的字幕行（空稿或全是注释行）。")

    srt = build_srt(lines, args.duration, args.offset, args.gap)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(srt)
        print(f"[srtgen] 完成：{len(lines)} 条字幕 → {args.out}（总时长 {args.duration}s）")
    else:
        sys.stdout.write(srt)


if __name__ == "__main__":
    main()
