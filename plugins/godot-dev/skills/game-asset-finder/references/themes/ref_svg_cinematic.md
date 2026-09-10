# SVG 主题：电影/沉浸风 (cinematic)

## 八、电影/沉浸风 `cinematic`

**参考品牌**：Runway, PlayStation, BMW-M, Ferrari, Sanity, Resend

### 调色板
```
背景：    #000000 / #030303 / #0b0b0b
文字：    #ffffff / #b9b9b9 / #a1a4a5
边框：    rgba(255,255,255,0.06~0.14)
点缀色：  #f36458（珊瑚红）/ #0052ef（电蓝）/ #ffce21（PS金）
```

### 按钮造型
- **Pill 主色**：圆角大，实心点缀色
- **极细描边**：1px rgba白色描边，暗部背景

### SVG 模板 — PlayStation 风蓝色 pill 按钮
```xml
<svg width="180" height="48" xmlns="http://www.w3.org/2000/svg">
  <rect width="180" height="48" rx="8" fill="#000000"/>
  <rect x="8" y="8" width="164" height="32" rx="16" fill="#0070d1"/>
  <text x="90" y="28" text-anchor="middle" fill="#ffffff"
        font-size="14" font-family="system-ui" font-weight="300" letter-spacing="1">继续游戏</text>
</svg>
```

### SVG 模板 — PS Plus 金色等级徽章
```xml
<svg width="80" height="28" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ffce21"/>
      <stop offset="50%" stop-color="#f5a623"/>
      <stop offset="100%" stop-color="#ee8e00"/>
    </linearGradient>
  </defs>
  <rect width="80" height="28" rx="14" fill="url(#gold)"/>
  <text x="40" y="18" text-anchor="middle" fill="#000000"
        font-size="10" font-family="system-ui" font-weight="700">GOLD</text>
</svg>
```
