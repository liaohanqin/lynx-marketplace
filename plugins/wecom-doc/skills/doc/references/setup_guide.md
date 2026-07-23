# 企微文档 Skill 环境搭建指南

## 前提条件

- Python 3.8+
- macOS / Linux / Windows
- 能在浏览器中正常访问企微文档的账号

## 第一步：安装 Playwright

```bash
pip3 install playwright
python3 -m playwright install chromium
```

如果网络受限，可使用镜像：

```bash
pip3 install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright python3 -m playwright install chromium
```

## 第二步：导出 Cookie

有两种方式导出企微文档的登录 Cookie。

### 方式一：使用自动导出工具（推荐）

运行 `export_cookies.py` 脚本，会打开一个浏览器窗口引导登录：

```bash
python3 scripts/export_cookies.py
```

按提示在浏览器中完成登录，工具会自动检测登录成功并导出 Cookie 到 `~/.wecom-doc-cookies.json`。

### 方式二：手动导出（备选）

1. 在 Chrome 中打开任意企微文档并确保已登录
2. 按 `F12` 打开 DevTools → 切换到 **Application** 标签页
3. 左侧选择 **Cookies** → `https://doc.weixin.qq.com`
4. 右键点击 Cookie 列表区域 → **Copy all as JSON** (如果没有此选项，见下方手动方式)
5. 将内容粘贴保存到 `~/.wecom-doc-cookies.json`

如果 DevTools 没有直接导出 JSON 的选项，可以在 **Console** 中运行：

```javascript
// 在 doc.weixin.qq.com 页面的 Console 中执行
copy(document.cookie.split('; ').map(c => {
  const [name, ...rest] = c.split('=');
  return { name, value: rest.join('='), domain: '.weixin.qq.com', path: '/' };
}));
```

然后粘贴保存为 `~/.wecom-doc-cookies.json`。

## 第三步：验证环境

```bash
python3 scripts/check_env.py
```

所有检查项显示 ✅ 即可正常使用。

## Cookie 过期处理

企微文档的 Cookie 通常在 **7~30 天**后过期。过期后脚本会提示"Cookie 已过期"，重新运行 `export_cookies.py` 即可刷新。

## Cookie 文件格式

Cookie 文件为 JSON 数组格式，每个条目至少包含 `name` 和 `value` 字段：

```json
[
  {
    "name": "wedoc_skey",
    "value": "xxx",
    "domain": ".weixin.qq.com",
    "path": "/"
  }
]
```
