#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补漏：行内 <code> 元素原文未出现在译文里时，以〔原文〕形式补到该译文块末尾。

为什么需要这一步（实测结论）：
LLM 翻译时会把行内 <code>（CodeInText、Player.gd、_process、customercare@packt.com 等）
当作"举例说明"整个省略，即使提示词明确要求保留。实测整本书漏掉 1545 处 / 796 个块。

特点：
- 确定性兜底，不依赖模型表现
- 幂等：补过之后原文已存在于译文，重复运行结果为 0
- 只做追加，不改动已有正确译文

重译或精修任何章节之后都必须再跑一次本脚本。
"""
import argparse
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    BLOCK_TAGS, content_files, kind_of, find_cn, norm,
    localname, parse_xhtml, serialize, pack_epub,
)

MAX_CODE_LEN = 200


def own_codes(el):
    """只取元素直系区域内的行内 code 文本，不跨入后代块（后代块各自处理）。"""
    out = []

    def walk(node, top=False):
        if not isinstance(node.tag, str):
            return
        ln = localname(node)
        # code 必须先于 SKIP_SUBTREE 判断，因为 SKIP_SUBTREE 里也含 "code"
        if ln == "code":
            t = norm("".join(node.itertext()))
            if t:
                out.append(t)
            return
        if ln in {"pre"}:
            return
        if ln in BLOCK_TAGS and not top:
            return
        for c in node:
            walk(c)

    walk(el, top=True)
    return out


def is_noise(t):
    """过滤 >、* 之类无实义符号与超长片段。"""
    if not re.search(r"[0-9A-Za-z]", t):
        return True
    return not (2 <= len(t) <= MAX_CODE_LEN)


def process(data, stats, examples):
    root = parse_xhtml(data)
    for el in list(root.iter()):
        if not isinstance(el.tag, str):
            continue
        ln = localname(el)
        if ln not in BLOCK_TAGS:
            continue
        cls = (el.get("class") or "").split()
        if "cn" in cls or "cn-h" in cls:
            continue
        if ln == "h1" and el.get("class") == "chapterNumber":
            continue
        if not re.search(r"[A-Za-z]", norm("".join(el.itertext()))[:400]):
            continue
        cn = find_cn(el, kind_of(el))
        if cn is None:
            continue
        cn_text = cn.text or ""
        missing = []
        for t in own_codes(el):
            if is_noise(t) or t in missing:
                continue
            if t.lower() in cn_text.lower():
                continue
            missing.append(t)
        if missing:
            add = " ".join("〔%s〕" % t for t in missing)
            cn.text = (cn_text.rstrip() + " " + add) if cn_text.strip() else add
            stats["fixed"] += 1
            stats["codes"] += len(missing)
            if len(examples) < 10:
                examples.append((missing, norm("".join(el.itertext()))[:110]))
    return serialize(root.getroottree())


def main():
    ap = argparse.ArgumentParser(description="补回译文中丢失的行内代码原文")
    ap.add_argument("--src", required=True, help="待修补的双语 EPUB")
    ap.add_argument("--out", required=True, help="输出路径")
    ap.add_argument("--files", default="", help="只处理指定文件，逗号分隔")
    ap.add_argument("--exclude", default="", help="排除文件名关键词，逗号分隔")
    ap.add_argument("--apply", action="store_true", help="真正写回，否则只报告")
    args = ap.parse_args()

    zin = zipfile.ZipFile(args.src)
    if args.files:
        files = [f.strip() for f in args.files.split(",") if f.strip()]
    else:
        ex = args.exclude.split(",") if args.exclude else None
        files = content_files(zin, exclude=ex)
    files = [f for f in files if f in zin.namelist()]

    stats = {"fixed": 0, "codes": 0}
    examples = []
    new_contents = {}
    for n in files:
        before = stats["fixed"]
        new_contents[n] = process(zin.read(n), stats, examples)
        print("  %-28s 修补 %d 块" % (os.path.basename(n), stats["fixed"] - before))

    print("\n合计：修补 %d 个译文块，补回 %d 处代码原文" % (stats["fixed"], stats["codes"]))
    for missing, en in examples:
        print("\n补回: %s" % " ".join("〔%s〕" % m for m in missing))
        print("  EN: %s" % en)

    if args.apply and stats["fixed"]:
        pack_epub(args.src, new_contents, args.out)
        print("\n已写出：%s" % args.out)
    elif not args.apply:
        print("\n（预览模式，未写回。加 --apply 生效）")


if __name__ == "__main__":
    main()
