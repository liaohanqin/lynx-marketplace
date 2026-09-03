#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验双语 EPUB 产物。

校验项：
1. mimetype 为第一个条目且未压缩（STORED）
2. zip 完整性
3. 每个英文块都紧跟一个非空译文块（逐块核对，不做抽样）
4. CSS 已注入
5. 条目数与源文件一致（无资源丢失）

注意：统计英文块时必须排除译文块本身（class="cn"/"cn-h"），
否则译文里残留的 ASCII 术语会让统计虚高，导致误报"缺失译文"。
"""
import argparse
import os

import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    content_files, collect_blocks, kind_of, find_cn, is_cn, parse_xhtml,
)


def main():
    ap = argparse.ArgumentParser(description="校验双语 EPUB 产物")
    ap.add_argument("--epub", required=True, help="待校验的双语 EPUB")
    ap.add_argument("--source", default=None, help="原始 EPUB，用于比对条目数")
    ap.add_argument("--files", default="", help="只校验指定文件，逗号分隔")
    ap.add_argument("--exclude", default="", help="排除文件名关键词，逗号分隔")
    args = ap.parse_args()

    z = zipfile.ZipFile(args.epub)
    info = z.infolist()
    ok = True

    first = info[0]
    checks = [
        ("mimetype 为首个条目", first.filename == "mimetype"),
        ("mimetype 未压缩(STORED)", first.compress_type == zipfile.ZIP_STORED),
        ("mimetype 内容正确", z.read("mimetype").decode().strip() == "application/epub+zip"),
        ("zip 完整性", z.testzip() is None),
    ]
    if args.source:
        zs = zipfile.ZipFile(args.source)
        checks.append(("条目数与源一致 (%d/%d)" % (len(info), len(zs.infolist())),
                       len(info) == len(zs.infolist())))

    print("=== 结构校验 ===")
    for name, passed in checks:
        print("  [%s] %s" % ("OK" if passed else "!!", name))
        ok = ok and passed

    print("\n=== 逐块中英对应 ===")
    # 必须与 translate.py 使用同一套选取逻辑，否则会把 nav/toc/index 等
    # 本就不打算翻译的文件全部报成"缺失译文"
    if args.files:
        files = [f.strip() for f in args.files.split(",") if f.strip()]
    else:
        ex = args.exclude.split(",") if args.exclude else None
        files = content_files(z, exclude=ex)
    files = [f for f in files if f in z.namelist()]
    total_code = total_code_ok = 0
    total_en = total_ok = 0
    for n in files:
        root = parse_xhtml(z.read(n))
        en = ok_n = code_n = code_ok_n = 0
        # 必须复用 collect_blocks（translate.py 用的同一个函数）。
        # 自己重写一套筛选逻辑会与翻译口径漂移，把"直系文本无字母、只有子块有"的
        # 容器块也算成待译文块，从而误报缺失译文。
        for el, _text, _kind, codes in collect_blocks(root):
            en += 1
            cn = find_cn(el, _kind)
            if cn is None or not (cn.text or "").strip():
                continue
            ok_n += 1
            # 行内代码原文必须出现在译文中（且是就地保留，不是追加到末尾）
            if codes:
                cnt = cn.text
                code_n += len(codes)
                code_ok_n += sum(1 for c in codes if c.lower() in cnt.lower())
        cn_all = sum(1 for e in root.iter()
                     if isinstance(e.tag, str)
                     and (e.get("class") or "") in ("cn", "cn-h"))
        total_en += en
        total_ok += ok_n
        total_code += code_n
        total_code_ok += code_ok_n
        flag = "OK" if ok_n == en else "!! 缺 %d" % (en - ok_n)
        if code_n and code_ok_n != code_n:
            flag += " | 代码丢 %d" % (code_n - code_ok_n)
        print("  %-28s 英文块=%-5d 有译文=%-5d 译文块=%-5d %s"
              % (os.path.basename(n), en, ok_n, cn_all, flag))
        ok = ok and (ok_n == en) and (code_ok_n == code_n)

    print("\n合计：英文块 %d，有译文 %d，缺失 %d" % (total_en, total_ok, total_en - total_ok))
    print("行内代码原文：应保留 %d 处，译文中已有 %d 处，丢失 %d 处"
          % (total_code, total_code_ok, total_code - total_code_ok))

    css_ok = any("bilingual injection" in z.read(n).decode("utf-8", "ignore")
                 for n in files if n in z.namelist())
    print("CSS 注入: %s" % ("OK" if css_ok else "!! 缺失"))
    ok = ok and css_ok

    print("\n结论：%s" % ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
