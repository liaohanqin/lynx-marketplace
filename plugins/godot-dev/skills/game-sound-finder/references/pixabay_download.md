# Pixabay 下载策略

Pixabay 详情页 HTML 底部嵌有 `<script type="application/ld+json">` 结构化数据，其中 `contentUrl` 字段即音频 CDN 地址，无需 API key。

> **合规说明**：curl 需设置浏览器 User-Agent，否则 Pixabay 返回空页面。此行为可能违反 [Pixabay 服务条款](https://pixabay.com/service/terms/)，风险由用户自行承担。

## 完整提取 + 下载命令

```bash
mkdir -p sounds/

DIRECT_URL=$(curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://pixabay.com/sound-effects/SLUG-ID/" \
  | grep -o '"contentUrl":"[^"]*"' | head -1 \
  | grep -o 'https://cdn[^"]*' \
  | sed 's|/download/audio/|/audio/|' | sed 's|?.*||')

if [[ -z "$DIRECT_URL" ]]; then
  echo "[ERROR] 未能提取到下载链接，页面结构可能已变更，请改用备选网站"
  exit 1
fi

curl -L --output "sounds/FILENAME.mp3" "$DIRECT_URL"
```

## URL 转换规则

```
原始：https://cdn.pixabay.com/download/audio/2024/01/09/audio_28c453a8ff.mp3?filename=xxx.mp3
直链：https://cdn.pixabay.com/audio/2024/01/09/audio_28c453a8ff.mp3
```

规则：`/download/audio/` → `/audio/`，去掉 `?filename=...` 参数。

## 失败处理

| 现象 | 原因 | 处理 |
|------|------|------|
| `DIRECT_URL` 为空 | 页面结构变更 | 改用备选网站 |
| curl 返回 403/404 | CDN 链接过期 | 重新从详情页提取 |
| 网络超时 | 网络问题 | 稍后重试，或让用户手动下载 |
