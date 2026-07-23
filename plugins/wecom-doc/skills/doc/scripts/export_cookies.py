#!/usr/bin/env python3
"""
交互式导出企微文档 Cookie。

启动一个可见的 Chromium 浏览器窗口，引导用户登录企微文档，
登录成功后自动导出 Cookie 到文件。

用法:
    python3 export_cookies.py [--output <path>] [--timeout <seconds>]

参数:
    --output    Cookie 输出文件路径，默认为 ~/.wecom-doc-cookies.json
    --timeout   登录页打开超时时间（秒），默认 30
"""

import argparse
import json
import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import DEFAULT_COOKIE_FILE, require_playwright, safe_goto


# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="交互式导出企微文档 Cookie")
    parser.add_argument(
        "--output",
        default=DEFAULT_COOKIE_FILE,
        help=f"Cookie 输出路径 (默认: {DEFAULT_COOKIE_FILE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="登录页打开超时秒数 (默认: 30)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# 登录检测用的关键 Cookie 名称
# ---------------------------------------------------------------------------

KEY_COOKIE_INDICATORS = [
    "wwapp.vid",
    "wwapp.cid",
    "wedoc_skey",
    "wedoc_sid",
    "wedoc_ticket",
]


# ---------------------------------------------------------------------------
# 登录成功页面关键词
# ---------------------------------------------------------------------------

LOGGED_IN_KEYWORDS = ["最近文档", "我的文档", "新建"]


# ---------------------------------------------------------------------------
# 过滤出企微相关的 Cookie（最小化域名范围）
# ---------------------------------------------------------------------------

TRUSTED_COOKIE_DOMAIN_SUFFIXES = (
    "doc.weixin.qq.com",
    "weixin.qq.com",
)


def is_trusted_cookie_domain(domain):
    """判断 Cookie 域名是否在允许范围内。"""
    normalized = (domain or "").strip().lower().lstrip(".")
    if not normalized:
        return False
    return any(
        normalized == suffix or normalized.endswith(f".{suffix}")
        for suffix in TRUSTED_COOKIE_DOMAIN_SUFFIXES
    )


def filter_wecom_cookies(all_cookies):
    """从所有 Cookie 中筛选出企微文档相关的。"""
    return [
        c for c in all_cookies
        if is_trusted_cookie_domain(c.get("domain", ""))
    ]


def has_key_cookies(cookies, min_count=3):
    """检查是否包含关键登录 Cookie。"""
    cookie_names = {c["name"] for c in cookies}
    has_key = any(k in cookie_names for k in KEY_COOKIE_INDICATORS)
    return has_key and len(cookies) >= min_count


def tighten_cookie_file_permissions(cookie_file):
    """收紧 Cookie 文件权限为当前用户可读写（0600）。"""
    if os.name == "nt":
        return

    try:
        os.chmod(cookie_file, 0o600)
    except OSError as e:
        print(
            f"警告: 无法收紧 Cookie 文件权限: {e}\n"
            f"建议手动执行: chmod 600 {cookie_file}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    if args.timeout <= 0:
        print("错误: --timeout 必须为正整数秒。", file=sys.stderr)
        sys.exit(1)

    sync_playwright = require_playwright()

    # 检查已有文件
    if os.path.exists(args.output):
        print(f"提示: Cookie 文件已存在: {args.output}", file=sys.stderr)
        print("本次导出将覆盖已有文件。\n", file=sys.stderr)

    login_url = "https://doc.weixin.qq.com"

    print("=" * 60)
    print("企微文档 Cookie 导出工具")
    print("=" * 60)
    print()
    print("即将打开浏览器窗口，请在浏览器中完成以下步骤：")
    print("  1. 选择「企业身份登录」或「个人身份登录」")
    print("  2. 扫码或输入密码完成登录")
    print("  3. 登录成功后，本工具会自动检测并导出 Cookie")
    print()
    print("按 Ctrl+C 可随时取消。")
    print()

    # 用于 Ctrl+C 时正常关闭浏览器
    browser_ref = {"browser": None}

    def signal_handler(_sig, _frame):
        print("\n\n已取消。正在关闭浏览器...", file=sys.stderr)
        if browser_ref["browser"]:
            try:
                browser_ref["browser"].close()
            except Exception:
                pass
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        browser_ref["browser"] = browser

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print("正在打开企微文档登录页面...")
        safe_goto(page, login_url, args.timeout * 1000)

        # 轮询检测登录状态
        print("等待登录...")
        max_wait_seconds = 300  # 最多等 5 分钟
        poll_interval_ms = 2000
        max_polls = max_wait_seconds * 1000 // poll_interval_ms

        logged_in = False
        doc_cookies = []

        for _ in range(max_polls):
            page.wait_for_timeout(poll_interval_ms)

            all_cookies = context.cookies()
            doc_cookies = filter_wecom_cookies(all_cookies)

            # 方法1: 通过关键 Cookie 判断
            if has_key_cookies(doc_cookies):
                logged_in = True
                break

            # 方法2: 通过页面内容判断
            try:
                body_text = page.inner_text("body")
                if any(kw in body_text for kw in LOGGED_IN_KEYWORDS):
                    logged_in = True
                    # 再等一下确保 Cookie 完整
                    page.wait_for_timeout(3000)
                    doc_cookies = filter_wecom_cookies(context.cookies())
                    break
            except Exception:
                pass

        if not logged_in:
            print(
                "超时: 5 分钟内未检测到登录成功。请重新运行本工具重试。",
                file=sys.stderr,
            )
            browser.close()
            sys.exit(1)

        # 保存 Cookie
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(doc_cookies, f, ensure_ascii=False, indent=2)

        tighten_cookie_file_permissions(args.output)

        browser.close()

        print()
        print(f"登录成功！已导出 {len(doc_cookies)} 个 Cookie 到: {args.output}")
        print()
        print("现在可以使用 read_doc.py 和 write_doc.py 来读写企微文档了。")
        print("Cookie 通常在 7~30 天后过期，届时重新运行本工具即可。")


if __name__ == "__main__":
    main()
