#!/usr/bin/env python3
"""
向企微文档写入/追加内容。

企微文档使用 Canvas 渲染，编辑操作通过模拟键盘输入完成。
本脚本通过 Playwright 加载文档后，模拟键盘操作写入内容。

用法:
    python3 write_doc.py <doc_url> --text <content> [--cookie-file <path>] [--mode append|replace] [--timeout <seconds>]
    python3 write_doc.py <doc_url> --file <path> [--cookie-file <path>] [--mode append|replace] [--timeout <seconds>]

退出码:
    0  成功
    1  参数错误 / 依赖缺失 / Cookie 文件问题
    2  Cookie 过期或登录失效
    3  无编辑权限 / 写入验证失败 / 不支持的文档类型
"""

import argparse
import sys
import os
from urllib.parse import urlparse

# 将 scripts 目录加入搜索路径，以便导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (
    DEFAULT_COOKIE_FILE,
    activate_editor,
    check_login_required,
    create_browser_context,
    get_modifier,
    load_cookies,
    normalize_cookies,
    require_playwright,
    safe_goto,
    validate_url,
    wait_for_doc_render,
)


# ---------------------------------------------------------------------------
# 解析参数
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="向企微文档写入内容")
    parser.add_argument("doc_url", help="企微文档 URL")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="要写入的文本内容")
    group.add_argument("--file", help="从文件读取要写入的内容")
    parser.add_argument(
        "--cookie-file",
        default=DEFAULT_COOKIE_FILE,
        help=f"Cookie 文件路径 (默认: {DEFAULT_COOKIE_FILE})",
    )
    parser.add_argument(
        "--mode",
        choices=["append", "replace"],
        default="append",
        help="写入模式 (默认: append)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="页面加载超时秒数 (默认: 30)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# 获取写入内容
# ---------------------------------------------------------------------------

def resolve_content(args):
    """根据参数获取要写入的内容，返回字符串。"""
    if args.text:
        content = args.text
    else:
        if not os.path.exists(args.file):
            print(f"错误: 文件不存在: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()

    if not content.strip():
        print("错误: 写入内容为空。", file=sys.stderr)
        sys.exit(1)

    return content


# ---------------------------------------------------------------------------
# 写入类型校验
# ---------------------------------------------------------------------------

def ensure_doc_write_supported(doc_url):
    """仅允许普通文档(doc)写入，拒绝 sheet/slide 等类型。"""
    path = urlparse(doc_url).path or ""
    if path.startswith("/doc/"):
        return

    print(
        "错误: 当前仅支持普通文档(doc)写入，不支持表格(sheet)、智能表格(smartsheet)或演示文稿(slide)写入。\n"
        f"  收到: {doc_url}",
        file=sys.stderr,
    )
    sys.exit(3)


# ---------------------------------------------------------------------------
# 只读检测
# ---------------------------------------------------------------------------

def check_readonly(page):
    """检测文档是否为只读（无编辑权限）。

    返回 True 表示文档只读，False 表示可编辑。
    """
    # 检查是否存在"只读"/"查看"标识
    readonly = page.evaluate("""() => {
        // 方法1: 检查工具栏是否被隐藏或禁用
        const toolbar = document.querySelector('.toolbar-area, .editor-toolbar');
        if (toolbar) {
            const style = window.getComputedStyle(toolbar);
            if (style.display === 'none' || style.visibility === 'hidden') {
                return true;
            }
        }

        // 方法2: 检查页面文本中是否有只读标识
        const bodyText = document.body.innerText || '';
        if (bodyText.includes('只读') || bodyText.includes('仅查看')) {
            return true;
        }

        // 方法3: 检查是否有编辑入口按钮（说明当前不在编辑模式）
        const editBtn = document.querySelector('[class*="request-edit"], [class*="apply-edit"]');
        if (editBtn) {
            return true;
        }

        return false;
    }""")
    return readonly


# ---------------------------------------------------------------------------
# 逐段输入内容（带进度反馈）
# ---------------------------------------------------------------------------

def type_content(page, content):
    """逐段输入内容，大文本时显示进度。"""
    lines = content.split("\n")
    total = len(lines)
    show_progress = total > 10  # 超过 10 行才显示进度

    for i, line in enumerate(lines):
        if line:
            page.keyboard.type(line, delay=5)
        if i < total - 1:
            page.keyboard.press("Enter")

        # 每 20 行报告一次进度
        if show_progress and (i + 1) % 20 == 0:
            pct = (i + 1) * 100 // total
            print(f"  写入进度: {i + 1}/{total} 行 ({pct}%)", file=sys.stderr)

    if show_progress:
        print(f"  写入进度: {total}/{total} 行 (100%)", file=sys.stderr)


# ---------------------------------------------------------------------------
# 写入后验证
# ---------------------------------------------------------------------------

def verify_write(page, expected_snippet):
    """写入后通过全选+复制验证内容是否包含预期片段。

    返回 True 表示验证通过。
    """
    modifier = get_modifier()

    page.wait_for_timeout(2000)

    # 全选+复制
    page.keyboard.press(f"{modifier}+a")
    page.wait_for_timeout(1000)
    page.keyboard.press(f"{modifier}+c")
    page.wait_for_timeout(1000)

    # 从剪贴板读取
    text = page.evaluate("""async () => {
        try {
            return await navigator.clipboard.readText();
        } catch (e) {
            return '';
        }
    }""")

    if not text:
        return False

    # 取预期内容的前 50 个非空字符作为验证片段
    snippet = expected_snippet.strip()[:50]
    return snippet in text


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # 校验 URL
    url_error = validate_url(args.doc_url)
    if url_error:
        print(f"错误: {url_error}", file=sys.stderr)
        sys.exit(1)

    ensure_doc_write_supported(args.doc_url)

    # 获取写入内容
    content = resolve_content(args)

    # 加载 Cookie
    cookies = load_cookies(args.cookie_file)

    # 确保 Playwright 已安装
    sync_playwright = require_playwright()

    modifier = get_modifier()

    with sync_playwright() as p:
        browser, context = create_browser_context(p, headless=True)
        context.add_cookies(normalize_cookies(cookies))

        page = context.new_page()
        timeout_ms = args.timeout * 1000

        print(f"正在加载文档: {args.doc_url}", file=sys.stderr)
        safe_goto(page, args.doc_url, timeout_ms)

        # 检查登录
        page.wait_for_timeout(3000)
        if check_login_required(page):
            print(
                "错误: Cookie 已过期或无效，页面要求登录。\n"
                "请重新运行 export_cookies.py 导出 Cookie。",
                file=sys.stderr,
            )
            browser.close()
            sys.exit(2)

        # 等待渲染
        print("等待文档渲染...", file=sys.stderr)
        rendered = wait_for_doc_render(page, timeout_ms)
        if not rendered:
            print("警告: 渲染超时，尝试继续...", file=sys.stderr)

        # 检测只读权限
        if check_readonly(page):
            print(
                "错误: 当前账号对此文档没有编辑权限（只读/仅查看）。\n"
                "请联系文档所有者授予编辑权限后重试。",
                file=sys.stderr,
            )
            browser.close()
            sys.exit(3)

        # 激活编辑器
        activate_editor(page)

        # 执行写入
        if args.mode == "replace":
            print("模式: 替换全部内容", file=sys.stderr)
            page.keyboard.press(f"{modifier}+a")
            page.wait_for_timeout(1000)
            page.keyboard.press("Backspace")
            page.wait_for_timeout(500)
        else:
            print("模式: 追加到末尾", file=sys.stderr)
            page.keyboard.press(f"{modifier}+End")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")

        print("正在写入内容...", file=sys.stderr)
        type_content(page, content)

        # 等待自动保存
        print("等待自动保存...", file=sys.stderr)
        page.wait_for_timeout(5000)

        # 写入验证
        print("验证写入结果...", file=sys.stderr)
        if verify_write(page, content):
            print("写入完成！验证通过。", file=sys.stderr)
            browser.close()
            return

        print(
            "错误: 写入验证未通过，内容可能未成功写入。\n"
            "可能原因：无编辑权限、文档已锁定、或自动保存尚未完成。\n"
            "建议用 read_doc.py 读取文档确认。",
            file=sys.stderr,
        )
        browser.close()
        sys.exit(3)


if __name__ == "__main__":
    main()
