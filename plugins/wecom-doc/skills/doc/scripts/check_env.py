#!/usr/bin/env python3
"""
检查企微文档 Skill 的运行环境。

验证 Python 版本、Playwright 安装状态、Chromium 浏览器、Cookie 文件是否就绪。

用法:
    python3 check_env.py [--cookie-file <path>]
"""

import argparse
import json
import os
import sys
import shutil
import time


def parse_args():
    parser = argparse.ArgumentParser(description="检查企微文档 Skill 运行环境")
    parser.add_argument(
        "--cookie-file",
        default=os.path.expanduser("~/.wecom-doc-cookies.json"),
        help="Cookie 文件路径 (默认: ~/.wecom-doc-cookies.json)",
    )
    return parser.parse_args()


def check_item(name, passed, message=""):
    """打印检查结果，返回 passed。"""
    status = "✅" if passed else "❌"
    suffix = f" — {message}" if message else ""
    print(f"  {status} {name}{suffix}")
    return passed


def check_warning(name, message):
    """打印警告项。"""
    print(f"  ⚠️  {name} — {message}")


def check_cookie_file_permissions(cookie_file):
    """检查 Cookie 文件权限是否过宽（仅 Unix 生效）。"""
    if os.name == "nt":
        return
    if not os.path.exists(cookie_file):
        return

    try:
        mode = os.stat(cookie_file).st_mode & 0o777
    except OSError as e:
        check_warning("Cookie 文件权限", f"无法读取文件权限: {e}")
        return

    if mode & 0o077:
        check_warning(
            "Cookie 文件权限",
            f"当前权限为 {oct(mode)}，建议执行: chmod 600 {cookie_file}",
        )


def check_python_version():
    """检查 Python 版本是否 >= 3.8。"""
    v = sys.version_info
    ok = v >= (3, 8)
    msg = f"Python {v.major}.{v.minor}.{v.micro}"
    if not ok:
        msg += "（需要 3.8+）"
    return check_item("Python 版本", ok, msg)


def check_pip():
    """检查 pip 是否可用。"""
    ok = shutil.which("pip3") is not None or shutil.which("pip") is not None
    return check_item("pip 可用", ok, "" if ok else "未找到 pip3/pip")


def check_playwright():
    """检查 Playwright 是否已安装。返回是否安装成功。"""
    try:
        import playwright  # noqa: F401
        return check_item("Playwright", True, "已安装")
    except ImportError:
        return check_item("Playwright", False, "未安装 — 运行: pip3 install playwright")


def check_chromium(pw_installed):
    """检查 Chromium 浏览器是否已安装。"""
    if not pw_installed:
        return check_item("Chromium 浏览器", False, "需要先安装 Playwright")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
            return check_item("Chromium 浏览器", True, "已安装")
    except Exception:
        return check_item(
            "Chromium 浏览器", False,
            "未安装 — 运行: python3 -m playwright install chromium",
        )


def check_cookie_file(cookie_file):
    """检查 Cookie 文件是否存在、格式正确、是否过期。"""
    if not os.path.exists(cookie_file):
        return check_item(
            "Cookie 文件", False,
            f"不存在 — 运行 export_cookies.py 导出",
        )

    try:
        with open(cookie_file, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return check_item("Cookie 文件", False, f"JSON 格式损坏: {cookie_file}")

    if isinstance(data, dict):
        data = data.get("cookies", [])

    if not isinstance(data, list) or len(data) == 0:
        return check_item("Cookie 文件", False, "文件内容为空")

    # 检查 Cookie 过期状态
    now = time.time()
    expired_count = 0
    earliest_expire = float("inf")
    for c in data:
        expires = c.get("expires", c.get("expirationDate", -1))
        if isinstance(expires, (int, float)) and expires > 0:
            if expires < now:
                expired_count += 1
            elif expires < earliest_expire:
                earliest_expire = expires

    msg = f"已找到 ({len(data)} 个 Cookie) @ {cookie_file}"
    ok = True

    if expired_count == len(data):
        msg = f"所有 {len(data)} 个 Cookie 均已过期 — 请重新运行 export_cookies.py"
        ok = False
    elif expired_count > 0:
        check_item("Cookie 文件", True, msg)
        check_warning(
            "Cookie 过期",
            f"{expired_count}/{len(data)} 个 Cookie 已过期，可能影响访问",
        )
        return True

    if ok and earliest_expire < float("inf"):
        remaining_days = (earliest_expire - now) / 86400
        if remaining_days < 3:
            check_item("Cookie 文件", True, msg)
            check_warning(
                "Cookie 即将过期",
                f"最早的 Cookie 将在 {remaining_days:.1f} 天后过期，建议提前刷新",
            )
            return True

    return check_item("Cookie 文件", ok, msg)


def main():
    args = parse_args()
    all_ok = True

    print("企微文档 Skill 环境检查")
    print("=" * 40)

    all_ok &= check_python_version()
    all_ok &= check_pip()
    pw_ok = check_playwright()
    all_ok &= pw_ok
    all_ok &= check_chromium(pw_ok)
    all_ok &= check_cookie_file(args.cookie_file)
    check_cookie_file_permissions(args.cookie_file)

    print()
    if all_ok:
        print("✅ 所有检查通过！可以正常使用企微文档 Skill。")
    else:
        print("⚠️  部分检查未通过，请按提示修复后重试。")
        sys.exit(1)


if __name__ == "__main__":
    main()
