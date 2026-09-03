#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EPUB 中英双语化主管线：解析 → 批量翻译 → 写回 → 打包。

设计要点
- 原 HTML 结构完全不改，只在每个英文块之后插入一个中文块
- 代码块（pre/code）不翻译
- 译文按原文哈希缓存，支持断点续传
- 批量失败自动重试，再降级逐条重发，绝不中断整本书
- 并发请求（默认 6）大幅提升吞吐

用法见 SKILL.md。运行 --help 查看全部参数。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    content_files, collect_blocks, write_back, strip_cn, inject_css,
    parse_xhtml, serialize, pack_epub, restore_ph, missing_ph,
)

API_URL = os.environ.get("EPUB_TRANSLATE_API", "https://copilot.tencent.com/v2/chat/completions")
DEFAULT_MODEL = os.environ.get("EPUB_TRANSLATE_MODEL", "hy3-ioa")

BATCH_CHARS = 5000
MAX_BLOCKS = 25
MAX_TOKENS = 16000
REQUEST_TIMEOUT = 300

SYSTEM_PROMPT = """你是资深技术书籍译者，精通该领域的技术术语与软件架构。
请将用户给出的英文条目逐条翻译成简体中文。

输出格式（严格遵守）：
[编号] 译文

规则：
1. 每条译文以 [编号] 开头，编号与输入完全一致；不得合并、拆分、省略或新增条目。
2. 只输出译文，不要任何解释、前言、后记或代码块标记。
3. 技术术语、API 名、类名、方法名、语言关键字保留英文不译。
4. 代码标识符、函数名、变量名、文件路径、命令行、URL、邮箱保持原样，一个字符都不得省略。
5. 技术含义务必准确，简体中文表达通顺自然，符合中文技术书行文习惯。
6. 保留原文的强调语义，不要添加原文没有的内容。
7. 文中出现的 ⟦数字⟧ 是代码片段占位符，**必须原样保留在译文中的对应位置**，
   不得翻译、省略、改写、拆散或挪到句末。占位符前后的中文要自然衔接。"""

_log_fh = None


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    if _log_fh:
        _log_fh.write(line + "\n")
        _log_fh.flush()


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def llm_translate_batch(items, model, retries=3):
    """items: [(idx, text)] → {idx: 译文}；失败返回 None。

    注意：该接口不支持非流式请求（返回 code 11101），必须 stream=True。
    """
    payload = {
        "model": model,
        "stream": True,
        "max_tokens": MAX_TOKENS,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "请翻译以下条目：\n\n"
                                        + "\n".join("[%d] %s" % (i, t) for i, t in items)},
        ],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    api_key = os.environ.get("CODEBUDDY_API_KEY", "")
    if not api_key:
        raise RuntimeError("未设置环境变量 CODEBUDDY_API_KEY，无法调用翻译接口")

    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                API_URL, data=body,
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + api_key,
                         "Accept": "text/event-stream"},
            )
            chunks = []
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                for raw in resp:
                    s = raw.decode("utf-8", "ignore").strip()
                    if not s.startswith("data:"):
                        continue
                    data = s[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        chunks.append(obj["choices"][0]["delta"].get("content", "") or "")
                    except Exception:
                        continue
            parsed = parse_numbered("".join(chunks))
            missing = [i for i, _ in items if i not in parsed]
            if not missing:
                return parsed
            last_err = "缺少编号 %s" % missing[:5]
        except urllib.error.HTTPError as e:
            last_err = "HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:200])
        except Exception as e:  # noqa: BLE001
            last_err = "%s: %s" % (type(e).__name__, str(e)[:200])
        wait = 2 ** attempt * 3
        log("    批次重试 %d/%d（%s），等待 %ds" % (attempt + 1, retries, last_err, wait))
        time.sleep(wait)
    return None


def parse_numbered(text):
    """解析 '[编号] 译文' 格式；译文可跨多行。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    out = {}
    for part in re.split(r"(?=^\[\d+\])", text, flags=re.MULTILINE):
        m = re.match(r"^\[(\d+)\]\s*(.*)$", part.strip(), flags=re.DOTALL)
        if not m:
            continue
        val = re.sub(r"\s*\n\s*", "", m.group(2).strip())
        if val:
            out[int(m.group(1))] = val
    return out


# --------------------------------------------------------------------------- #
# 缓存
# --------------------------------------------------------------------------- #
def ckey(text):
    """无行内代码的块：沿用原文哈希（与既有缓存兼容）。"""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def phkey(text, codes):
    """含行内代码的块：缓存键 = 占位符文本 + 代码原文。

    必须把 codes 纳入键：表格里常见「文本结构完全相同、但代码内容不同」的多行
    （如 ⟦0⟧ : Contains ⟦1⟧, ⟦2⟧, ⟦3⟧ 对应 Player 行与 Goblin 行）。
    若只按占位符文本做键，这些行会命中同一条缓存、共用同一个译文，互相串扰。
    同时要区别于旧的不带占位符的原文键。
    """
    return hashlib.sha1(("PH|" + text + "\x00" + "\x00".join(codes)).encode("utf-8")).hexdigest()


def load_cache(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            log("缓存损坏，重新开始：" + path)
    return {}


def save_cache(path, cache):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# 单文件处理
# --------------------------------------------------------------------------- #
def translate_file(zf, name, cache, cache_path, model, workers, stats,
                   limit_blocks=0, retranslate=False):
    tree = parse_xhtml(zf.read(name)).getroottree()
    root = tree.getroot()

    if retranslate:
        stripped = strip_cn(root)
        if stripped:
            log("[%s] 清除旧译文 %d 个" % (os.path.basename(name), stripped))

    blocks = collect_blocks(root)
    if limit_blocks:
        blocks = blocks[:limit_blocks]
    total = len(blocks)

    # 为每个块确定缓存键：
    # - 无行内代码 → 沿用旧键 sha1(原文)，与既有缓存兼容
    # - 有行内代码 → 用占位符键 sha1("PH|"+占位符文本)，译文会把代码留在上下文中
    #   若旧缓存里的译文已包含全部代码原文，则直接复用（省配额），并迁移到新键
    keys = {}
    todo = []
    reused = 0
    for el, text, kind, codes in blocks:
        if codes:
            k = phkey(text, codes)
            if k in cache:
                keys[id(el)] = k
                continue
            raw = restore_ph(text, codes)[0]
            legacy = cache.get(ckey(raw))
            if legacy and all(c in legacy for c in codes):
                cache[k] = legacy
                keys[id(el)] = k
                reused += 1
                continue
        else:
            k = ckey(text)
            if k in cache:
                keys[id(el)] = k
                continue
        keys[id(el)] = k
        todo.append((k, text, codes))

    log("[%s] 共 %d 块，待翻译 %d 块（复用旧译文 %d 块）"
        % (os.path.basename(name), total, len(todo), reused))

    batches, cur, cur_chars = [], [], 0
    for k, text, codes in todo:
        if cur and (cur_chars + len(text) > BATCH_CHARS or len(cur) >= MAX_BLOCKS):
            batches.append(cur)
            cur, cur_chars = [], 0
        cur.append((k, text, codes))
        cur_chars += len(text)
    if cur:
        batches.append(cur)

    def finalize(raw_trans, codes):
        """校验占位符齐全后替换回原文。缺失则判为失败，触发重译。"""
        if raw_trans is None:
            return None
        miss = missing_ph(raw_trans, len(codes))
        if miss:
            return None
        result, _ = restore_ph(raw_trans, codes)
        return result

    def do_batch(arg):
        bi, batch = arg
        res = llm_translate_batch([(n, t) for n, (k, t, c) in enumerate(batch)], model)
        if res is None:
            single = {}
            for k, text, codes in batch:  # 降级：逐条重发
                one = llm_translate_batch([(0, text)], model, retries=2)
                single[k] = finalize((one or {}).get(0), codes)
                time.sleep(0.5)
            return bi, batch, single
        return bi, batch, {k: finalize(res.get(n), c)
                           for n, (k, t, c) in enumerate(batch)}

    if batches:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            for bi, batch, result in ex.map(do_batch, list(enumerate(batches, 1))):
                for k, text, codes in batch:
                    v = result.get(k)
                    if v:
                        cache[k] = v
                    else:
                        stats["failed"] += 1
                        log("    !! 该块译文丢失代码占位符，放弃：%s" % text[:60])
                stats["done"] += len(batch)
                save_cache(cache_path, cache)
                log("    批次 %d 完成 | 累计 %d/%d 块 | 失败 %d"
                    % (bi, stats["done"], stats["todo_total"], stats["failed"]))

    written = 0
    for el, text, kind, codes in blocks:
        cn = cache.get(keys.get(id(el)))
        if cn:
            write_back(el, cn, kind)
            written += 1
    inject_css(root)
    stats["written"] += written
    stats["blocks"] += total
    log("[%s] 写回译文 %d/%d 块" % (os.path.basename(name), written, total))
    return serialize(tree)


# --------------------------------------------------------------------------- #
def main():
    global _log_fh
    ap = argparse.ArgumentParser(description="将 EPUB 翻译为中英对照版本")
    ap.add_argument("--src", required=True, help="源 EPUB 路径")
    ap.add_argument("--out", required=True, help="输出 EPUB 路径")
    ap.add_argument("--cache", required=True, help="译文缓存 JSON 路径（支持断点续传）")
    ap.add_argument("--log", default=None, help="日志文件路径（默认仅输出到 stdout）")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--workers", type=int, default=6, help="并发请求数（默认 6）")
    ap.add_argument("--files", default="", help="只处理指定文件，逗号分隔（相对 EPUB 内路径）")
    ap.add_argument("--exclude", default="",
                    help="排除的文件名关键词，逗号分隔（默认已排除 cover/nav/toc/index）")
    ap.add_argument("--retranslate", action="store_true", help="先清除已有译文再重译")
    ap.add_argument("--limit-files", type=int, default=0, help="只处理前 N 个文件（试跑）")
    ap.add_argument("--limit-blocks", type=int, default=0, help="每个文件只翻前 N 块（试跑）")
    args = ap.parse_args()

    if args.log:
        _log_fh = open(args.log, "a", encoding="utf-8")

    log("启动：src=%s model=%s workers=%d" % (args.src, args.model, args.workers))
    zin = zipfile.ZipFile(args.src)

    if args.files:
        process = [f.strip() for f in args.files.split(",") if f.strip()]
    else:
        ex = args.exclude.split(",") if args.exclude else None
        process = content_files(zin, exclude=ex, limit_files=args.limit_files)
    process = [n for n in process if n in zin.namelist()]
    for n in [f for f in (args.files.split(",") if args.files else []) if f.strip()]:
        if n.strip() not in zin.namelist():
            log("!! 源 EPUB 中不存在：%s" % n.strip())
    if not process:
        log("!! 没有可处理的文件")
        sys.exit(1)
    log("待处理文件 %d 个：%s" % (len(process), ", ".join(os.path.basename(n) for n in process[:5])
                                + (" ..." if len(process) > 5 else "")))

    cache = load_cache(args.cache)
    stats = {"done": 0, "failed": 0, "written": 0, "blocks": 0, "todo_total": 0}
    todo_n = reused_n = 0
    for n in process:
        root = parse_xhtml(zin.read(n))
        bs = collect_blocks(root)
        if args.limit_blocks:
            bs = bs[:args.limit_blocks]
        for _, t, _, codes in bs:
            if codes:
                if phkey(t, codes) in cache:
                    reused_n += 1
                    continue
                raw = restore_ph(t, codes)[0]
                legacy = cache.get(ckey(raw))
                if legacy and all(c in legacy for c in codes):
                    reused_n += 1
                    continue
            elif ckey(t) in cache:
                reused_n += 1
                continue
            todo_n += 1
    stats["todo_total"] = todo_n
    log("待翻译总块数：%d，可直接复用：%d，缓存条目 %d" % (todo_n, reused_n, len(cache)))

    new_contents = {}
    for fi, name in enumerate(process, 1):
        log("### 文件 %d/%d：%s" % (fi, len(process), name))
        new_contents[name] = translate_file(
            zin, name, cache, args.cache, args.model, args.workers, stats,
            args.limit_blocks, args.retranslate,
        )
        log("    进度：文件 %d/%d 完成 | 失败 %d" % (fi, len(process), stats["failed"]))

    pack_epub(args.src, new_contents, args.out)
    log("完成：%s（%.2f MB）" % (args.out, os.path.getsize(args.out) / 1024 / 1024))
    log("统计：总块 %d，写回译文 %d，失败 %d" % (stats["blocks"], stats["written"], stats["failed"]))
    if _log_fh:
        _log_fh.close()


if __name__ == "__main__":
    main()
