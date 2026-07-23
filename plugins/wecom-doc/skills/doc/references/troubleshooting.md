# 故障排查指南

## 常见问题

### 1. "Cookie 已过期或无效，页面要求登录"

**原因**: Cookie 过期或不完整。

**解决**:
```bash
python3 scripts/export_cookies.py
```
重新登录导出 Cookie 即可。

### 2. "未能提取到文档内容"

**可能原因与解决方案**:

| 原因 | 解决方案 |
|------|---------|
| 无权限访问该文档 | 确认登录账号有文档的阅读权限 |
| 文档类型不支持 | 目前支持普通文档(doc)与在线表格(sheet)读取；收集表、思维导图等暂不支持 |
| 页面结构变更 | 更新 Skill 中的 DOM 选择器 |
| 渲染超时 | 尝试增大 `--timeout` 参数值 |

### 3. "未找到可编辑区域"（写入时）

**可能原因**:
- 当前账号只有**阅读权限**，没有编辑权限
- 文档被管理员设为只读
- 文档类型不支持在线编辑

**解决**: 联系文档所有者授予编辑权限。

### 4. Playwright 安装失败

**症状**: `playwright install chromium` 下载超时或失败。

**解决**:
```bash
# 使用国内镜像
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright python3 -m playwright install chromium
```

### 5. 无头模式下无法加载页面

**症状**: 脚本长时间无响应或报 timeout 错误。

**排查步骤**:
1. 先运行 `check_env.py` 确认环境正常
2. 尝试用可见模式调试：在脚本中将 `headless=True` 改为 `headless=False`
3. 检查网络是否需要代理

### 6. 写入内容后格式丢失

**原因**: 写入操作通过模拟键盘输入完成，仅支持纯文本。

**说明**: Markdown 格式的 `#`、`**` 等标记会作为纯文本输入，不会自动转换为企微文档的富文本格式。

## 支持的文档类型

| 类型 | 读取 | 写入 | 说明 |
|------|------|------|------|
| 普通文档 (doc) | ✅ | ✅ | 完整支持 |
| 在线表格 (sheet) | ✅ | ❌ | 仅支持读取 |
| 演示文稿 (slide) | ⚠️ | ❌ | 可提取文本，格式可能丢失 |
| 收集表 | ❌ | ❌ | 暂不支持 |
| 思维导图 | ❌ | ❌ | 暂不支持 |

### 7. "URL 不是企微文档地址"

**原因**: 传入的 URL 不是 `doc.weixin.qq.com` 域名或路径格式不对。

**解决**: 确认 URL 格式为 `https://doc.weixin.qq.com/doc/w3_XXXXX`（doc/sheet/slide）。

### 8. Cookie 即将过期提示

`check_env.py` 会检测 Cookie 过期时间，如果距离过期不到 3 天会发出警告。

**解决**: 提前运行 `export_cookies.py` 刷新 Cookie，避免使用中突然失效。

## 诊断命令

```bash
# 检查完整环境（含 Cookie 过期检测）
python3 scripts/check_env.py

# 测试读取
python3 scripts/read_doc.py <url>

# 验证 Cookie 是否有效（会输出到 stderr）
python3 scripts/read_doc.py <url> 2>&1 | head -5
```
