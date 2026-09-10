# 前置检查

在开始搜索和下载之前，依次执行以下检查。任一检查失败时立即告知用户并给出修复建议，不继续后续步骤。

## 1. 网络连通性检查

```bash
curl -s --max-time 5 -o /dev/null -w "%{http_code}" https://pixabay.com/
```

| 结果 | 处理 |
|------|------|
| 返回 `200` 或 `301` | 网络正常，继续 |
| 超时或 `000` | 提示用户检查网络连接或代理设置，终止流程 |
| 返回其他 HTTP 错误 | 提示 Pixabay 暂时不可访问，建议稍后重试或直接切换备选网站 |

## 2. ffmpeg 可用性检查

仅在用户需要后处理（裁剪/压缩/转格式）时才必须检查；纯下载任务可跳过。

```bash
ffmpeg -version 2>&1 | head -1
```

| 结果 | 处理 |
|------|------|
| 输出 `ffmpeg version ...` | ffmpeg 可用，继续 |
| `command not found` / 报错 | 告知用户 ffmpeg 未安装，给出安装指引（见下） |

### ffmpeg 安装指引

- **Windows**：`winget install ffmpeg` 或下载 https://ffmpeg.org/download.html，解压后将 `bin/` 加入 `PATH`
- **macOS**：`brew install ffmpeg`
- **Linux (Debian/Ubuntu)**：`sudo apt install ffmpeg`
- 安装完成后重新执行前置检查

> 如果用户只需要下载不需要后处理，可跳过 ffmpeg 检查，告知用户："下载功能不需要 ffmpeg，后处理功能（裁剪/压缩/转格式）需要它。"
