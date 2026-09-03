#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EPUB 双语化共享工具：块解析、译文定位、打包。

被 translate.py / fix_codes.py / verify.py 共同引用。
"""
import os
import re
import shutil
import zipfile
from lxml import etree

XHTML_NS = "http://www.w3.org/1999/xhtml"
NS = "{%s}" % XHTML_NS

BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "blockquote"}
HEADING_TAGS = {"h1", "h2", "h3", "h4"}
SKIP_SUBTREE = {"pre", "code"}

# 注入到每个 xhtml 的译文样式
CSS = """
/* ---- bilingual injection ---- */
.cn, .cn-h {
  font-family: "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", serif;
  color: #3182ce;
  font-size: 0.95em;
  line-height: 1.75;
  margin: 0.35em 0 1em;
  text-align: justify;
}
.cn-h { font-weight: bold; font-size: 1em; margin: 0.2em 0 0.9em; }
li .cn { margin: 0.2em 0 0.5em; }
blockquote .cn { margin: 0.4em 0 0.6em; }
"""


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


# 行内代码占位符：形如 ⟦0⟧。用罕见字符对，避免与正文标点混淆，
# 也避免 LLM 把它当普通标点改写。
PH_OPEN = "\u27e6"
PH_CLOSE = "\u27e7"
PH_RE = re.compile(re.escape(PH_OPEN) + r"(\d+)" + re.escape(PH_CLOSE))


def ph(i):
    return "%s%d%s" % (PH_OPEN, i, PH_CLOSE)


def restore_ph(text, codes):
    """把译文里的占位符替换回代码原文；返回 (译文, 缺失的占位符编号列表)。"""
    missing = []

    def sub(m):
        i = int(m.group(1))
        if i < len(codes):
            return codes[i]
        missing.append(i)
        return m.group(0)

    return PH_RE.sub(sub, text), missing


def missing_ph(text, n):
    """返回译文里缺失的占位符编号集合（用于判定该块是否需要重译）。"""
    found = {int(m) for m in PH_RE.findall(text)}
    return [i for i in range(n) if i not in found]


def localname(el):
    """取无命名空间的标签名；非元素节点返回 None。"""
    return el.tag.split("}")[-1] if isinstance(el.tag, str) else None


def parse_xhtml(data):
    """用 XML 解析器（recover=True）解析 XHTML。

    实测：对 Kobo 风格 EPUB，XML 解析器往返保真度 100%（p 数一致、长度比 1.0），
    优于 HTML 解析器（HTML 解析器会丢弃 xml 声明与 DOCTYPE）。
    """
    return etree.fromstring(data, etree.XMLParser(recover=True, resolve_entities=False))


def serialize(tree):
    return etree.tostring(tree, xml_declaration=True, encoding="UTF-8", method="xml")


# --------------------------------------------------------------------------- #
# EPUB 阅读顺序
# --------------------------------------------------------------------------- #
def spine_files(zf):
    """按 content.opf 的 spine 顺序返回正文章节文件名列表。

    返回为空时调用方应退化为「所有 xhtml」。
    """
    try:
        container = zf.read("META-INF/container.xml")
        croot = parse_xhtml(container)
        opf_path = None
        for el in croot.iter():
            if localname(el) == "rootfile":
                opf_path = el.get("full-path")
                break
        if not opf_path:
            return []
        base = os.path.dirname(opf_path)
        opf = parse_xhtml(zf.read(opf_path))
    except Exception:
        return []

    manifest = {}
    for el in opf.iter():
        if localname(el) == "item":
            iid, href = el.get("id"), el.get("href")
            if iid and href:
                manifest[iid] = os.path.normpath(os.path.join(base, href)).replace("\\", "/")

    order = []
    for el in opf.iter():
        if localname(el) == "itemref":
            idref = el.get("idref")
            if idref in manifest:
                order.append(manifest[idref])

    return [n for n in order if n.lower().endswith((".xhtml", ".html"))]


def all_xhtml(zf):
    return [n for n in zf.namelist() if n.lower().endswith((".xhtml", ".html"))]


# 默认排除：封面、目录、索引、广告页等无需翻译的条目
DEFAULT_EXCLUDE = ["cover", "nav", "toc", "title_page", "titlepage", "index", "other_books"]


def content_files(zf, exclude=None, limit_files=0):
    """选取待处理的正文文件。

    必须让 translate / fix_codes / verify 三个脚本使用**同一套**选取逻辑，
    否则 verify 会把"本就不打算翻译"的文件（nav/toc/index/cover）全部报成缺失译文。

    - exclude 为 None 时使用 DEFAULT_EXCLUDE；传空列表表示不排除任何文件。
    """
    files = spine_files(zf) or all_xhtml(zf)
    if exclude is None:
        exclude = DEFAULT_EXCLUDE
    if exclude:
        keys = [k.strip().lower() for k in exclude if k.strip()]
        files = [n for n in files
                 if not any(k in os.path.basename(n).lower() for k in keys)]
    if limit_files:
        files = files[:limit_files]
    return files


# --------------------------------------------------------------------------- #
# 块解析
# --------------------------------------------------------------------------- #
def has_skipped_ancestor(el):
    cur = el.getparent()
    while cur is not None:
        if localname(cur) in SKIP_SUBTREE:
            return True
        cur = cur.getparent()
    return False


def extract_text(el):
    """提取元素直系文本，返回 (带占位符的文本, 行内代码原文列表)。

    关键：行内 <code> 不用纯文本塞给 LLM，而是换成占位符 ⟦N⟧。
    若直接把代码当普通文本送进去，LLM 会把它当作"举例说明"整段吞掉，
    且事后只能把原文追加到译文末尾 —— 那已经破坏了译文的上下文。
    用占位符可以让原文**留在译文中它该在的位置**。

    只取直系文本：不跨入后代块元素（后代块各自单独处理），
    这样既不重复翻译，也不会漏掉容器的直系文本。
    """
    buf = []
    codes = []

    def walk(node, top=False):
        if not isinstance(node.tag, str):
            if node.text:
                buf.append(node.text)
            return
        ln = localname(node)
        # code 必须先于 SKIP_SUBTREE 判断（SKIP_SUBTREE 里也含 "code"）
        if ln == "code":
            t = norm("".join(node.itertext()))
            if t:
                buf.append(ph(len(codes)))
                codes.append(t)
            return
        if ln in SKIP_SUBTREE:
            return
        if ln in BLOCK_TAGS and not top:
            return
        if node.text:
            buf.append(node.text)
        for child in node:
            walk(child)
            if child.tail:
                buf.append(child.tail)

    walk(el, top=True)
    return norm("".join(buf)), codes


def collect_blocks(root):
    """返回 [(el, text, kind, codes)]，kind ∈ {p, li, h, bq, lead}

    - text 为**带占位符**的文本（行内 <code> 被替换为 ⟦N⟧），codes 是对应的原文列表
    - lead = 含后代块元素的容器（如内嵌 <p> 的 <li>），其译文需插在直系文本之后、
      第一个后代块之前；其余类型插在元素之后
    """
    blocks = []
    for el in root.iter():
        tag = localname(el)
        if tag not in BLOCK_TAGS:
            continue
        cls = el.get("class") or ""
        if is_cn(el):  # 已是译文块（cn 或 cn-h），跳过
            continue
        if tag == "h1" and cls == "chapterNumber":
            continue
        if has_skipped_ancestor(el):
            continue
        text, codes = extract_text(el)
        if len(text) < 2:
            continue
        if not re.search(r"[A-Za-z]", text):
            continue
        container = any(
            localname(d) in BLOCK_TAGS and not is_cn(d)
            for d in el.iterdescendants()
        )
        if tag in HEADING_TAGS:
            kind = "h"
        elif container:
            kind = "lead"
        elif tag == "blockquote":
            kind = "bq"
        elif tag == "li":
            kind = "li"
        else:
            kind = "p"
        blocks.append((el, text, kind, codes))
    return blocks


def kind_of(el):
    """判定块类型。注意：判定容器时必须排除已插入的译文块，否则会被误判为 lead。"""
    tag = localname(el)
    container = any(
        localname(d) in BLOCK_TAGS and not is_cn(d)
        for d in el.iterdescendants()
    )
    if tag in HEADING_TAGS:
        return "h"
    if container:
        return "lead"
    if tag == "blockquote":
        return "bq"
    if tag == "li":
        return "li"
    return "p"


def find_cn(el, kind):
    """定位英文块对应的译文块（class 为 cn / cn-h）。"""
    if kind == "li":
        cn = el[-1] if len(el) else None
    elif kind == "lead":
        first = None
        for d in el.iterdescendants():
            if localname(d) in BLOCK_TAGS and not is_cn(d):
                first = d
                break
        cn = first.getprevious() if first is not None else None
    else:
        cn = el.getnext()
    if cn is None or not isinstance(cn.tag, str):
        return None
    cls = cn.get("class") or ""
    return cn if cls in ("cn", "cn-h") else None


def is_cn(el):
    return isinstance(el.tag, str) and (el.get("class") or "") in ("cn", "cn-h")


# --------------------------------------------------------------------------- #
# 写回
# --------------------------------------------------------------------------- #
def write_back(el, cn, kind):
    """在原块之后（或内部）插入译文块，原 HTML 结构完全不动。"""
    new = etree.Element(NS + "p", attrib={"class": "cn-h" if kind == "h" else "cn"})
    new.text = cn
    if kind == "li":
        el.append(new)  # 插在 li 内部，避免破坏列表结构
    elif kind == "lead":
        first = None
        for d in el.iterdescendants():
            if localname(d) in BLOCK_TAGS and not is_cn(d):
                first = d
                break
        if first is not None:
            first.addprevious(new)  # 直系文本之后、第一个子块之前
        else:
            el.insert(0, new)
    else:
        el.addnext(new)


def strip_cn(root):
    """重译前清除已有译文块，避免叠加重复。"""
    removed = 0
    for el in list(root.iter()):
        if is_cn(el):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
                removed += 1
    return removed


def inject_css(root):
    for el in root.iter():
        if localname(el) == "head":
            for existing in el:
                if localname(existing) == "style" and "bilingual injection" in (existing.text or ""):
                    return False
            style = etree.Element(NS + "style", attrib={"type": "text/css"})
            style.text = CSS
            el.append(style)
            return True
    return False


# --------------------------------------------------------------------------- #
# 打包
# --------------------------------------------------------------------------- #
def pack_epub(src_path, new_contents, out_path):
    """重新打包 EPUB。

    两个硬性要求：
    1. mimetype 必须是第一个条目且不压缩（STORED），否则阅读器不识别。
    2. 跨文件系统时必须用 shutil.move —— /tmp 与 /mnt/c 之间 os.replace 会抛
       OSError: [Errno 18] Invalid cross-device link。
    """
    tmp = out_path + ".tmp"
    zin = zipfile.ZipFile(src_path)
    names = zin.namelist()
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        zout.writestr(info, "application/epub+zip")
        for name in names:
            if name == "mimetype":
                continue
            zout.writestr(name, new_contents.get(name, zin.read(name)), zipfile.ZIP_DEFLATED)
    zin.close()
    shutil.move(tmp, out_path)
    return out_path
