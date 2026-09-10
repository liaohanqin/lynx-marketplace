# SVG 主题：宇宙/史诗风 (space)

## 四、宇宙/史诗风 `space`

**参考品牌**：xAI, Together.AI, Mistral, Superhuman, Notion, Slack

### 调色板
```
背景：    #010120 / #000000
强调A：   #fc4c02（橙）→ #ef2cc1（洋红）→ #bdbbff（薰衣紫） 三色渐变
强调B：   #ff8105（日落橙）/ #ffd06a（金黄）
文字：    #ffffff / #a8a29e
```

### 按钮造型
- **渐变 pill**：三色线性渐变填充，pill 圆角

### SVG 模板 — 宇宙三色渐变按钮
```xml
<svg width="180" height="48" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="spaceGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#fc4c02"/>
      <stop offset="50%" stop-color="#ef2cc1"/>
      <stop offset="100%" stop-color="#bdbbff"/>
    </linearGradient>
  </defs>
  <rect width="180" height="48" rx="8" fill="#010120"/>
  <rect x="4" y="4" width="172" height="40" rx="20" fill="url(#spaceGrad)"/>
  <text x="90" y="28" text-anchor="middle" fill="#ffffff"
        font-size="14" font-family="system-ui" font-weight="600">EXPLORE</text>
</svg>
```

### SVG 模板 — 日落渐变背景板（Mistral 风）
```xml
<svg width="320" height="80" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="sunset" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffd06a"/>
      <stop offset="40%" stop-color="#ff8105"/>
      <stop offset="80%" stop-color="#fa520f"/>
      <stop offset="100%" stop-color="#c01f00"/>
    </linearGradient>
  </defs>
  <rect width="320" height="80" fill="url(#sunset)"/>
  <text x="160" y="48" text-anchor="middle" fill="#ffffff"
        font-size="28" font-family="Georgia,serif" font-weight="400">QUEST COMPLETE</text>
</svg>
```
