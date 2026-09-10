# SVG 主题：赛博朋克/科技风 (cyber)

## 一、赛博朋克/科技风 `cyber`

**参考品牌**：Linear, Raycast, ClickHouse, Framer, Composio, Sanity, Voltagent, HashiCorp, Verge, Resend

### 调色板
```
背景层：  #010102 / #0f0f0f / #000000
卡片层：  #181818 / #1f232b / #0a0a0c
描边：    rgba(255,255,255,0.06~0.14)
主色A：   #fcd535（电黄）/ #faff69（氙黄）/ #c2ef4e（电绿）
主色B：   #5e6ad2（薰衣草蓝）/ #0007cd（电蓝）/ #00d992（翠绿）
主色C：   #ffffff（白）/ #3cffd0（薄荷）
危险色：  #ff4d4d / #ff2047
成功色：  #33d17a / #11ff99
```

### 按钮造型
- **实色 pill**：`rx="9999"` + 主色填充，白色文字
- **描边 ghost**：透明填充 + 1px 主色描边，文字同主色
- **发光按钮**：fill + `filter: drop-shadow(0 0 8px 主色)`

### SVG 模板 — 发光按钮
```xml
<svg width="160" height="44" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="btnGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#5e6ad2"/>
      <stop offset="100%" stop-color="#0007cd"/>
    </linearGradient>
  </defs>
  <!-- 背景 -->
  <rect width="160" height="44" rx="4" fill="#010102"/>
  <!-- 发光按钮 -->
  <rect x="8" y="8" width="144" height="28" rx="14" fill="url(#btnGrad)" filter="url(#glow)"/>
  <text x="80" y="26" text-anchor="middle" fill="#ffffff" font-size="13" font-family="system-ui" font-weight="600">CONFIRM</text>
</svg>
```

### SVG 模板 — 描边 Ghost 按钮（深色背景）
```xml
<svg width="160" height="44" xmlns="http://www.w3.org/2000/svg">
  <rect width="160" height="44" rx="4" fill="#0f0f0f"/>
  <rect x="8" y="8" width="144" height="28" rx="14"
        fill="none" stroke="#faff69" stroke-width="1.5"/>
  <text x="80" y="26" text-anchor="middle" fill="#faff69"
        font-size="13" font-family="system-ui" font-weight="600">CANCEL</text>
</svg>
```

### SVG 模板 — 图标按钮（圆形）
```xml
<svg width="48" height="48" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="iconBg" cx="50%" cy="35%">
      <stop offset="0%" stop-color="#5e6ad2"/>
      <stop offset="100%" stop-color="#010102"/>
    </radialGradient>
  </defs>
  <circle cx="24" cy="24" r="22" fill="url(#iconBg)" stroke="#5e6ad2" stroke-width="1"/>
  <!-- 图标路径（示例：设置齿轮） -->
  <circle cx="24" cy="24" r="5" fill="none" stroke="#ffffff" stroke-width="1.5"/>
  <line x1="24" y1="12" x2="24" y2="16" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
  <line x1="24" y1="32" x2="24" y2="36" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
  <line x1="12" y1="24" x2="16" y2="24" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
  <line x1="32" y1="24" x2="36" y2="24" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
</svg>
```
