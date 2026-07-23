---
name: doc
description: 通过 Playwright + 登录 Cookie 读取与写入企微文档（doc.weixin.qq.com）。适用于读取文档/表格内容、写入普通文档，以及处理 Cookie 过期与环境诊断场景。
---

# 企微文档 Skill（读写）

通过 Playwright 无头浏览器 + 用户登录 Cookie，完成企微文档的读取与写入。

## 背景

企微文档在登录后主要通过 **Canvas** + WebSocket 渲染内容，静态 HTML 中通常拿不到正文文本。
本 Skill 采用以下方案：

- **读取**：模拟 `全选 + 复制`，再通过 `navigator.clipboard.readText()` 从剪贴板取回纯文本。
- **写入**：对编辑器模拟键盘输入（仅纯文本）。

## 使用前检查

先确认环境可用：

```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/check_env.py
```

若检查失败，请查看 `references/setup_guide.md`。

依赖要求：
- Python 3.8+
- Playwright（`pip3 install playwright`）
- Chromium（`python3 -m playwright install chromium`）
- 可用 Cookie 文件：`~/.wecom-doc-cookies.json`

## 首次配置（导出 Cookie）

首次使用先导出 Cookie：

```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/export_cookies.py
```

流程：
1. 脚本打开浏览器
2. 用户扫码/密码登录企微文档
3. 登录成功后自动保存 Cookie 到 `~/.wecom-doc-cookies.json`

可选参数：
- `--output <path>`：自定义 Cookie 输出路径
- `--timeout <seconds>`：登录页打开超时（默认 30）

## 常用工作流

### 1) 读取文档/表格

```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/read_doc.py "<doc_url>"
```

常用参数：
- `--timeout 60`：慢网络下增大等待时间
- `--output result.txt`：输出到文件
- `--cookie-file <path>`：指定 Cookie 路径

输出说明：
- `stdout`：标题 + 正文纯文本
- `stderr`：状态与错误信息

### 2) 写入普通文档（仅 doc）

```bash
# 追加写入
python3 ${CODEBUDDY_SKILL_DIR}/scripts/write_doc.py "<doc_url>" --text "要追加的内容"

# 覆盖写入
python3 ${CODEBUDDY_SKILL_DIR}/scripts/write_doc.py "<doc_url>" --text "新内容" --mode replace

# 从文件写入
python3 ${CODEBUDDY_SKILL_DIR}/scripts/write_doc.py "<doc_url>" --file content.txt --mode append
```

注意：
- 仅支持 `doc` 类型链接写入；`sheet`/`smartsheet`/`slide` 不支持写入
- 写入是键盘模拟输入，仅支持纯文本
- 账号必须有编辑权限
- 建议 `--mode replace` 前先用 `read_doc.py` 备份

### 3) 环境诊断

```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/check_env.py
```

该脚本会检查 Python / Playwright / Chromium / Cookie 状态，并提示 Cookie 是否即将过期。

## 错误处理

| 退出码 | 含义 | 建议处理 |
|---|---|---|
| 0 | 成功 | 无 |
| 1 | 参数错误 / 依赖缺失 / Cookie 文件异常 / URL 非法 | 运行 `check_env.py`，修复参数或环境 |
| 2 | Cookie 过期或登录失效 | 重新执行 `export_cookies.py` 刷新 Cookie |
| 3 | 内容提取失败 / 无编辑权限 / 写入校验失败 / 文档类型不支持写入 | 检查文档权限、文档类型与 `--timeout` |

### Cookie 过期处理

出现退出码 `2` 时：
1. 不要使用同一份 Cookie 重试
2. 立即重新导出 Cookie：`export_cookies.py`
3. 再执行原命令

## URL 规范

支持以下 URL 形态：
- 普通文档：`https://doc.weixin.qq.com/doc/w3_XXXXX`
- 在线表格：`https://doc.weixin.qq.com/sheet/e3_XXXXX`
- 智能表格：`https://doc.weixin.qq.com/smartsheet/s3_XXXXX`
- 演示文稿：`https://doc.weixin.qq.com/slide/p3_XXXXX`

共享链接中的 `scode` 参数应保留。

## 文档类型支持矩阵

| 类型 | 读取 | 写入 |
|---|---|---|
| 普通文档（doc） | ✅ | ✅ |
| 在线表格（sheet） | ✅ | ❌ |
| 智能表格（smartsheet） | ✅ | ❌ |
| 演示文稿（slide） | ⚠️ 部分支持 | ❌ |
| 收集表/表单 | ❌ | ❌ |
| 思维导图 | ❌ | ❌ |

## 已知限制

- Cookie 鉴权通常 7~30 天过期，需定期刷新
- 写入仅纯文本，不保留富文本样式（加粗、标题等）
- 表格写入暂不支持
- 大文档/慢网络时建议增大 `--timeout`
- 仅支持 `doc.weixin.qq.com` 域名链接
