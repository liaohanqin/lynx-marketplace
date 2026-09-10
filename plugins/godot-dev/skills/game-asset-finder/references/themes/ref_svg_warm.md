# SVG 主题：暖色温馨风 (warm)

## 五、暖色温馨风 `warm`

**参考品牌**：Claude, Cursor, Zapier, Intercom, PostHog, ElevenLabs, Warp, Lovable, Replicate, Mistral

### 调色板
```
背景：    #faf9f5（奶油）/ #fff8e0（米黄）/ #f9f7f3（骨白）
主色：    #cc785c（珊瑚）/ #ff4f00（橙红）/ #fa520f（深橙）
文字：    #1c1c1e / #292524 / #201515
暖灰：    #c9c0ad / #dad2c1
强调绿：  #f7a501（琥珀黄）
```

### 按钮造型
- **中圆角 (8px)**：`rx="8"`，温和不激进
- **暖色实心**：珊瑚/橙色系，无渐变或轻微渐变

### SVG 模板 — 珊瑚色暖按钮（Claude 风）
```xml
<svg width="160" height="44" xmlns="http://www.w3.org/2000/svg">
  <rect width="160" height="44" rx="10" fill="#faf9f5"/>
  <rect x="8" y="8" width="144" height="28" rx="8" fill="#cc785c"/>
  <text x="80" y="26" text-anchor="middle" fill="#ffffff"
        font-size="13" font-family="Georgia,serif" font-weight="600">继续</text>
</svg>
```

### SVG 模板 — 琥珀黄进度条（PostHog 风）
```xml
<svg width="200" height="28" xmlns="http://www.w3.org/2000/svg">
  <rect width="200" height="16" y="6" rx="4" fill="#dcdfd2"/>
  <rect width="120" height="16" y="6" rx="4" fill="#f7a501"/>
  <!-- 刻度 -->
  <rect x="40" y="4" width="1" height="20" fill="#eeefe9" opacity="0.6"/>
  <rect x="80" y="4" width="1" height="20" fill="#eeefe9" opacity="0.6"/>
  <rect x="120" y="4" width="1" height="20" fill="#eeefe9" opacity="0.6"/>
  <rect x="160" y="4" width="1" height="20" fill="#eeefe9" opacity="0.6"/>
</svg>
```
