# SVG 主题：奢华黑暗风 (luxury)

## 二、奢华黑暗风 `luxury`

**参考品牌**：Ferrari, Lamborghini, Bugatti, BMW-M, SpaceX, Runway

### 调色板
```
背景：    #000000 / #181818 / #030303
强调色：  #da291c（法拉利红）/ #ffc000（金）/ #ffffff（纯白）
文字：    #ffffff
边框：    rgba(255,255,255,0.1~0.2)
```

### 按钮造型
- **矩形（0圆角）**：Ferrari/Lamborghini 风格，锐角工程美学
- **极细 ghost pill**：Bugatti/SpaceX，1px 白色描边，透明填充
- **全出血横条**：宽度100%的行式按钮

### SVG 模板 — 法拉利红矩形按钮
```xml
<svg width="160" height="44" xmlns="http://www.w3.org/2000/svg">
  <rect width="160" height="44" fill="#181818"/>
  <rect x="8" y="8" width="144" height="28" rx="0" fill="#da291c"/>
  <text x="80" y="26" text-anchor="middle" fill="#ffffff"
        font-size="12" font-family="Arial" font-weight="700" letter-spacing="2">PLAY</text>
</svg>
```

### SVG 模板 — 金色点缀血条（Lamborghini 风）
```xml
<svg width="200" height="20" xmlns="http://www.w3.org/2000/svg">
  <!-- 底部轨道 -->
  <rect width="200" height="12" y="4" rx="0" fill="#111111" stroke="#333333" stroke-width="1"/>
  <!-- 血量 -->
  <rect width="140" height="12" y="4" rx="0" fill="#ffc000"/>
  <!-- 金色标记 -->
  <rect x="140" y="2" width="2" height="16" fill="#ffffff" opacity="0.8"/>
</svg>
```

### SVG 模板 — SpaceX Ghost Pill 按钮
```xml
<svg width="160" height="44" xmlns="http://www.w3.org/2000/svg">
  <rect width="160" height="44" fill="#000000"/>
  <rect x="8" y="8" width="144" height="28" rx="14"
        fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="1"/>
  <text x="80" y="26" text-anchor="middle" fill="#ffffff"
        font-size="11" font-family="Arial" font-weight="700" letter-spacing="3">LAUNCH</text>
</svg>
```
