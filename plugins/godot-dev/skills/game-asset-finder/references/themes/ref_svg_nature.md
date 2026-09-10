# SVG 主题：自然清新风 (nature)

## 三、自然清新风 `nature`

**参考品牌**：Wise, Supabase, MongoDB, Mintlify, Starbucks, Airbnb, ElevenLabs, Lovable

### 调色板
```
背景：    #ffffff / #fafaf0 / #f5f5f5
主色：    #9fe870（青柠）/ #3ecf8e（翠绿）/ #00ed64（亮绿）/ #006241（深绿）
暖色：    #ff385c（珊瑚红）/ #ff5600（橙）/ a7e5d3（薄荷）
中性：    #1c1c1e / #292524
```

### 按钮造型
- **饱和 pill**：圆角 9999，高饱和主色实心
- **多彩分类标签**：`rx="999"` 小 pill，不同类别不同色

### SVG 模板 — 翠绿圆角按钮（Supabase 风）
```xml
<svg width="160" height="44" xmlns="http://www.w3.org/2000/svg">
  <rect width="160" height="44" rx="8" fill="#ffffff"/>
  <rect x="8" y="8" width="144" height="28" rx="14" fill="#3ecf8e"/>
  <text x="80" y="26" text-anchor="middle" fill="#1c1c1e"
        font-size="13" font-family="system-ui" font-weight="700">开始游戏</text>
</svg>
```

### SVG 模板 — 青柠能量条（Wise 风）
```xml
<svg width="200" height="24" xmlns="http://www.w3.org/2000/svg">
  <rect width="200" height="14" y="5" rx="7" fill="#e5e5e5"/>
  <rect width="160" height="14" y="5" rx="7" fill="#9fe870"/>
  <text x="160" y="19" text-anchor="middle" fill="#1c1c1e"
        font-size="9" font-family="system-ui" font-weight="900">80%</text>
</svg>
```

### SVG 模板 — 薄荷渐变图标背景（ElevenLabs 风）
```xml
<svg width="64" height="64" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="mintGrad" cx="30%" cy="30%">
      <stop offset="0%" stop-color="#a7e5d3"/>
      <stop offset="50%" stop-color="#f4c5a8"/>
      <stop offset="100%" stop-color="#c8b8e0"/>
    </radialGradient>
  </defs>
  <rect width="64" height="64" rx="16" fill="url(#mintGrad)" opacity="0.6"/>
  <!-- 中间放具体图标 -->
</svg>
```
