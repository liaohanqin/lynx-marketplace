#!/usr/bin/env python3
"""
读取企微文档内容。

企微文档使用 Canvas 渲染，无法直接从 DOM 提取文本。
本脚本通过 Playwright 加载文档后，模拟"全选 → 复制"操作，
从剪贴板获取文档的纯文本内容。

用法:
    python3 read_doc.py <doc_url> [--cookie-file <path>] [--timeout <seconds>] [--output <path>]

退出码:
    0  成功
    1  参数错误 / 依赖缺失 / Cookie 文件问题
    2  Cookie 过期或登录失效
    3  内容提取失败
"""

import argparse
import sys
import os

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
    parser = argparse.ArgumentParser(description="读取企微文档内容")
    parser.add_argument("doc_url", help="企微文档 URL")
    parser.add_argument(
        "--cookie-file",
        default=DEFAULT_COOKIE_FILE,
        help=f"Cookie 文件路径 (默认: {DEFAULT_COOKIE_FILE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="页面加载超时秒数 (默认: 30)",
    )
    parser.add_argument("--output", help="输出文件路径，不指定则输出到 stdout")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# 提取文档内容
# ---------------------------------------------------------------------------

def extract_content_via_clipboard(page):
    """通过模拟全选+复制操作，从剪贴板获取文档文本。

    企微文档使用 Canvas 渲染，DOM 中没有文本内容。
    但编辑器支持 Ctrl/Cmd+A 全选和 Ctrl/Cmd+C 复制，
    复制后的纯文本可通过 navigator.clipboard API 读取。
    """
    modifier = get_modifier()

    # 点击文档区域使编辑器获得焦点
    activate_editor(page)

    # 全选
    page.keyboard.press(f"{modifier}+a")
    page.wait_for_timeout(2000)

    # 复制
    page.keyboard.press(f"{modifier}+c")
    page.wait_for_timeout(2000)

    # 从剪贴板读取
    text = page.evaluate("""async () => {
        try {
            return await navigator.clipboard.readText();
        } catch (e) {
            return '';
        }
    }""")

    return text or ""


def extract_title(page):
    """从多个来源尝试提取文档标题。"""
    # 从 title input 获取
    title_el = page.query_selector("#melo-doc-title")
    if title_el:
        value = title_el.get_attribute("value") or ""
        if value.strip():
            return value.strip()

    # 从 window.basicClientVars 获取（含智能表格等类型）
    title = page.evaluate("""() => {
        try {
            const v = window.basicClientVars;
            return (
                v?.docInfo?.title ||
                v?.sheetInfo?.title ||
                v?.smartsheetInfo?.title ||
                ''
            );
        } catch(e) { return ''; }
    }""")
    if title and title.strip():
        return title.strip()

    # 从 page title 获取
    page_title = page.title()
    if page_title and "企业微信文档" not in page_title:
        return page_title.strip()

    return "未知标题"


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

    # 加载 Cookie（内部处理 JSON 损坏、过期等问题）
    cookies = load_cookies(args.cookie_file)

    # 确保 Playwright 已安装
    sync_playwright = require_playwright()

    with sync_playwright() as p:
        browser, context = create_browser_context(p, headless=True)
        context.add_cookies(normalize_cookies(cookies))

        page = context.new_page()
        timeout_ms = args.timeout * 1000

        print(f"正在加载文档: {args.doc_url}", file=sys.stderr)
        safe_goto(page, args.doc_url, timeout_ms)

        # 检查登录状态（含 URL 重定向检测）
        page.wait_for_timeout(3000)
        if check_login_required(page):
            print(
                "错误: Cookie 已过期或无效，页面要求登录。\n"
                "请重新运行 export_cookies.py 导出 Cookie。",
                file=sys.stderr,
            )
            browser.close()
            sys.exit(2)

        # 等待 Canvas 渲染
        print("等待文档渲染...", file=sys.stderr)
        rendered = wait_for_doc_render(page, timeout_ms)
        if not rendered:
            print("警告: 等待渲染超时，尝试提取...", file=sys.stderr)

        # 提取标题
        title = extract_title(page)

        # 通过全选+复制提取内容
        print("提取文档内容...", file=sys.stderr)
        content = extract_content_via_clipboard(page)

        browser.close()

        if not content or not content.strip():
            print(
                "错误: 未能提取到文档内容。可能原因：\n"
                "  1. Cookie 无权限访问此文档\n"
                "  2. 文档类型不受支持（支持 doc/sheet/slide/smartsheet 等可复制的页面）\n"
                "  3. 文档内容为空\n"
                "  4. 渲染超时，尝试增大 --timeout 参数",
                file=sys.stderr,
            )
            sys.exit(3)

        # 组装输出
        output = f"# {title}\n\n{content.strip()}"

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"已保存到: {args.output}", file=sys.stderr)
        else:
            print(output)


if __name__ == "__main__":
    main()
