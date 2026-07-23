#!/usr/bin/env python3
"""
企微文档 Skill 公共模块。

提供 Cookie 加载/标准化、URL 校验、登录检测、文档渲染等待等共用功能，
供 read_doc.py 和 write_doc.py 共同调用，避免代码重复。
"""

import json
import os
import platform
import re
import sys
import time


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_COOKIE_FILE = os.path.expanduser("~/.wecom-doc-cookies.json")
WECOM_DOC_DOMAIN = "doc.weixin.qq.com"

# 企微文档 URL 合法路径前缀
VALID_URL_PATTERN = re.compile(
    r"^https?://doc\.weixin\.qq\.com/(doc|sheet|slide|flowchart|mindmap|form|smartsheet)/\w+"
)

# 页面出现以下文字则说明需要登录
LOGIN_INDICATORS = [
    "企业身份登录",
    "切换个人身份登录",
    "扫码登录",
    "请登录",
    "身份过期",
    "请重新登录",
]

# Canvas 选择器（企微文档用 Canvas 渲染内容）
CANVAS_SELECTORS = [
    "canvas.melo-page-main-view",
    "canvas.page-0",
    "canvas[class*='page-']",
    "canvas",
]

# 智能表格（smartsheet）可能以网格/画布混合方式渲染，优先等待可交互区域
SMARTSHEET_RENDER_SELECTORS = [
    "[role='grid']",
    "[role='gridcell']",
    "[class*='grid-view']",
    "[class*='spreadsheet']",
    "[class*='smartsheet']",
]


# ---------------------------------------------------------------------------
# URL 校验
# ---------------------------------------------------------------------------

def validate_url(url):
    """校验传入的 URL 是否为合法的企微文档地址。

    合法时返回 None，不合法时返回错误提示字符串。
    """
    if not url or not url.strip():
        return "URL 不能为空"
    if WECOM_DOC_DOMAIN not in url:
        return (
            f"URL 不是企微文档地址（需包含 {WECOM_DOC_DOMAIN}）。\n"
            f"  收到: {url}"
        )
    if not VALID_URL_PATTERN.match(url.split("?")[0]):
        return (
            "URL 路径格式不正确。示例:\n"
            "  https://doc.weixin.qq.com/doc/w3_XXXXX\n"
            "  https://doc.weixin.qq.com/smartsheet/s3_XXXXX\n"
            f"  收到: {url}"
        )
    return None


# ---------------------------------------------------------------------------
# Cookie 加载与标准化
# ---------------------------------------------------------------------------

def load_cookies(cookie_file):
    """从 JSON 文件加载 Cookie 列表。

    失败时打印错误到 stderr 并 sys.exit(1)。
    """
    if not os.path.exists(cookie_file):
        print(f"错误: Cookie 文件不存在: {cookie_file}", file=sys.stderr)
        print(
            "请先运行 export_cookies.py 导出 Cookie，"
            "或参考 references/setup_guide.md 手动导出。",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: Cookie 文件格式损坏，无法解析 JSON: {e}", file=sys.stderr)
        print(f"请删除 {cookie_file} 并重新运行 export_cookies.py 导出。", file=sys.stderr)
        sys.exit(1)

    if isinstance(cookies, dict) and "cookies" in cookies:
        cookies = cookies["cookies"]

    if not isinstance(cookies, list) or len(cookies) == 0:
        print("错误: Cookie 文件内容为空或格式不正确。", file=sys.stderr)
        print("请重新运行 export_cookies.py 导出 Cookie。", file=sys.stderr)
        sys.exit(1)

    # 检查 Cookie 是否可能已过期（通过 expires 字段）
    expired_count = 0
    now = time.time()
    for c in cookies:
        expires = c.get("expires", c.get("expirationDate", -1))
        if isinstance(expires, (int, float)) and 0 < expires < now:
            expired_count += 1

    if expired_count > 0 and expired_count == len(cookies):
        print(
            "警告: Cookie 文件中所有 Cookie 均已过期。\n"
            "请重新运行 export_cookies.py 刷新 Cookie。",
            file=sys.stderr,
        )
        sys.exit(2)
    elif expired_count > 0:
        print(
            f"警告: Cookie 文件中有 {expired_count}/{len(cookies)} 个 Cookie 已过期，"
            "可能影响访问。如遇问题请重新导出。",
            file=sys.stderr,
        )

    return cookies


def normalize_cookie(cookie):
    """将 Cookie 转换为 Playwright 期望的格式。"""
    entry = {
        "name": cookie.get("name", cookie.get("Name", "")),
        "value": cookie.get("value", cookie.get("Value", "")),
        "domain": cookie.get("domain", cookie.get("Domain", ".weixin.qq.com")),
        "path": cookie.get("path", cookie.get("Path", "/")),
    }
    same_site = cookie.get("sameSite", cookie.get("SameSite", "Lax"))
    same_site_map = {"no_restriction": "None", "lax": "Lax", "strict": "Strict"}
    if isinstance(same_site, str):
        entry["sameSite"] = same_site_map.get(same_site.lower(), same_site)
    else:
        entry["sameSite"] = "Lax"
    entry["httpOnly"] = cookie.get("httpOnly", cookie.get("HttpOnly", False))
    entry["secure"] = cookie.get("secure", cookie.get("Secure", False))
    return entry


def normalize_cookies(cookies):
    """批量标准化 Cookie 列表。"""
    return [normalize_cookie(c) for c in cookies]


# ---------------------------------------------------------------------------
# 操作系统相关
# ---------------------------------------------------------------------------

def get_modifier():
    """根据操作系统返回快捷键修饰符 (macOS: Meta, 其他: Control)。"""
    return "Meta" if platform.system() == "Darwin" else "Control"


# ---------------------------------------------------------------------------
# 浏览器上下文创建
# ---------------------------------------------------------------------------

def create_browser_context(playwright, headless=True):
    """创建带有标准配置的浏览器和上下文。

    返回 (browser, context) 元组。
    """
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
    )
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    return browser, context


# ---------------------------------------------------------------------------
# 登录状态检测
# ---------------------------------------------------------------------------

def check_login_required(page):
    """检查页面是否显示登录提示或被重定向到登录页。

    综合检查：
    1. 页面 URL 是否包含 login/passport 等登录相关路径
    2. 页面文本中是否包含登录提示关键词
    """
    # 检查 URL 是否被重定向到登录页
    current_url = page.url
    login_url_patterns = ["/login", "/passport", "/connect/oauth"]
    if any(pattern in current_url for pattern in login_url_patterns):
        return True

    # 检查页面文本
    try:
        page_text = page.inner_text("body")
    except Exception:
        return False
    return any(indicator in page_text for indicator in LOGIN_INDICATORS)


# ---------------------------------------------------------------------------
# 文档渲染等待
# ---------------------------------------------------------------------------

def wait_for_doc_render(page, timeout_ms):
    """等待企微文档 Canvas 渲染完成。

    智能表格会优先等待网格等可编辑区域，再回退到通用 Canvas 逻辑。

    返回 True 表示检测到 Canvas 渲染完成，False 表示超时（兜底等待后继续）。
    """
    is_smartsheet = "/smartsheet/" in (page.url or "")
    primary_selectors = (
        SMARTSHEET_RENDER_SELECTORS + CANVAS_SELECTORS if is_smartsheet else CANVAS_SELECTORS
    )

    # 先用短超时快速尝试各个特定选择器
    quick_timeout = min(3000, timeout_ms // max(len(primary_selectors), 1))
    for selector in primary_selectors[:-1]:
        try:
            page.wait_for_selector(selector, timeout=quick_timeout, state="attached")
            page.wait_for_timeout(5000)
            return True
        except Exception:
            continue

    # 最后用通用 canvas 选择器，给剩余超时
    remaining = max(timeout_ms - quick_timeout * (len(primary_selectors) - 1), 5000)
    try:
        page.wait_for_selector("canvas", timeout=remaining, state="attached")
        page.wait_for_timeout(5000)
        return True
    except Exception:
        pass

    # 兜底：等待一段时间
    page.wait_for_timeout(8000)
    return False


# ---------------------------------------------------------------------------
# 安全加载页面（带友好的超时错误）
# ---------------------------------------------------------------------------

def safe_goto(page, url, timeout_ms):
    """安全地加载页面，将 Playwright 超时异常转化为友好错误。"""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception as e:
        error_msg = str(e)
        if "Timeout" in error_msg or "timeout" in error_msg:
            print(
                f"错误: 页面加载超时（{timeout_ms // 1000}秒）。\n"
                "可能原因：\n"
                "  1. 网络连接慢或不稳定\n"
                "  2. 文档 URL 无效\n"
                "  3. 需要配置代理\n"
                "尝试增大 --timeout 参数值后重试。",
                file=sys.stderr,
            )
        elif "net::" in error_msg:
            print(
                f"错误: 网络连接失败: {error_msg}\n"
                "请检查网络连接是否正常。",
                file=sys.stderr,
            )
        else:
            print(f"错误: 页面加载失败: {error_msg}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# 编辑器激活与焦点
# ---------------------------------------------------------------------------

def activate_editor(page):
    """点击文档区域激活 Canvas 编辑器，使其获得焦点。

    智能表格优先点击网格区域，以便全选/复制作用于表格数据。
    """
    if "/smartsheet/" in (page.url or ""):
        try:
            grid = page.query_selector("[role='grid']")
            if grid:
                box = grid.bounding_box()
                if box and box["width"] > 0 and box["height"] > 0:
                    page.mouse.click(
                        box["x"] + min(120.0, box["width"] / 2),
                        box["y"] + min(40.0, box["height"] / 2),
                    )
                    page.wait_for_timeout(1000)
                    return
        except Exception:
            pass
    page.mouse.click(540, 400)
    page.wait_for_timeout(1000)


# ---------------------------------------------------------------------------
# Playwright 导入检查
# ---------------------------------------------------------------------------

def require_playwright():
    """尝试导入 playwright，失败时给出安装提示并退出。

    返回 sync_playwright 工厂函数。
    """
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        print(
            "错误: 需要安装 Playwright。运行:\n"
            "  pip3 install playwright && python3 -m playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)
