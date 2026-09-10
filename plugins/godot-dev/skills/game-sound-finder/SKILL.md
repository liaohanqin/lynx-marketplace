---
name: game-sound-finder
description: 免费音效搜索与下载专家，从 Pixabay 等免费音效网站检索音效文件，支持按关键词、时长、分类筛选并下载到本地。不适用于：付费音效网站、视频素材搜索、本地音频文件管理、非音频类媒体资源。
allowed-tools: WebFetch, WebSearch, Bash, Write, Read
---

# 音效搜索与下载专家

## 支持的网站

首选 Pixabay；结果不满意时切换备选网站。
> 完整站点列表及授权说明：Read `${CODEBUDDY_SKILL_DIR}/references/supported_sites.md`

---

## 工作流程

### 第0步：前置检查
执行网络连通性检查；若用户需要后处理则同时检查 ffmpeg 可用性。
> 检查命令与失败处理：Read `${CODEBUDDY_SKILL_DIR}/references/preflight_check.md`

### 第1步：解析需求
提取：搜索关键词（必须，中文翻译为英文）、时长范围、风格分类、下载目录（默认 `sounds/`）。
> 关键词翻译和时长筛选规则：Read `${CODEBUDDY_SKILL_DIR}/references/filter_keywords.md`

### 第2步：搜索
用 WebFetch 访问 Pixabay 搜索页，结果不满意时切换备选网站。

异常处理：
- WebFetch 失败 → 换用 WebSearch `site:pixabay.com/sound-effects KEYWORD`
- 搜索无结果 → 换同义词或切换网站
- 连续两个网站均无结果 → 告知用户并请其提供更多关键词或放宽时长限制

### 第3步：展示结果
以表格列出音效（名称、时长、风格、来源、详情页链接），询问用户选择。

### 第4步：获取直链并下载
- **Pixabay**：Read `${CODEBUDDY_SKILL_DIR}/references/pixabay_download.md` 获取完整提取命令
- **Scott Buckley**：WebFetch 曲目页，从页面提取 MP3 链接后 curl 下载；推荐曲目见 `${CODEBUDDY_SKILL_DIR}/references/scott_buckley_tracks.md`
- **其他网站**：WebFetch 详情页，找到直接 mp3 链接后 curl 下载

下载异常处理：
- **下载中断**：用 `curl -L -C - --retry 3 --retry-delay 2` 追加断点续传和自动重试，最多重试 3 次；3 次后仍失败则提示用户手动下载并给出直链
- **文件损坏检测**：下载完成后执行 `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 sounds/FILENAME.mp3`；若报错或 duration 为 0 则判定文件损坏，自动删除并重新下载一次；重试仍损坏则切换备选网站

### 第5步：后处理（按需）
用户提到裁剪/压缩/格式转换时触发：Read `${CODEBUDDY_SKILL_DIR}/references/audio_processing.md` 获取脚本用法。

触发词：
- "太长了"、"截取前N秒"、"只要X~Y秒" → 裁剪
- "文件太大"、"压缩到XXkb" → 大小压缩
- "转成ogg"、"改成wav" → 格式转换

### 第6步：结果报告
```
下载完成！共 N 个文件：
- sounds/filename.mp3 (XXkB)
授权说明：[每个文件的授权要求]
```

---

## 重要原则

1. **不使用 Pixabay API**：无 API key，禁止调用 `pixabay.com/api/`
2. **Pixabay 必须设置 User-Agent**：详见 `${CODEBUDDY_SKILL_DIR}/references/pixabay_download.md`
3. **所有推荐音效均免费授权**，告知用户授权要求（Pixabay 无需注明来源）
