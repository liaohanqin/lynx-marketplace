# SVG 主题：游乐/像素/卡通风 (playful)

## 六、游乐/像素/卡通风 `playful`

**参考品牌**：PostHog(刺猬), Clay(3D泥土), Miro(白板), Figma(多彩), Nintendo2001, Notion

### 调色板
```
背景：    #ffffff / #eeefe9（橄榄奶油）
主色：    #ffd02f（金丝雀黄）/ #f7a501（琥珀）/ #4262ff（蓝）
多彩：    粉/青/橙/薄荷/橘红，6色卡片系统
文字：    #23251d / #1c1c1e
圆角：    大圆角 12~16px，卡片 border 实心色
```

### 按钮造型
- **大圆角彩色**：每个按钮可用不同亮色
- **彩色描边卡片**：2px 实心彩色边框，白底

### SVG 模板 — 多彩分类按钮组
```xml
<svg width="240" height="52" xmlns="http://www.w3.org/2000/svg">
  <rect width="240" height="52" rx="12" fill="#ffffff"/>
  <!-- 按钮1 -->
  <rect x="4" y="8" width="68" height="36" rx="10" fill="#ffd02f"/>
  <text x="38" y="31" text-anchor="middle" fill="#23251d" font-size="12" font-weight="700">攻击</text>
  <!-- 按钮2 -->
  <rect x="76" y="8" width="68" height="36" rx="10" fill="#4262ff"/>
  <text x="110" y="31" text-anchor="middle" fill="#ffffff" font-size="12" font-weight="700">防御</text>
  <!-- 按钮3 -->
  <rect x="148" y="8" width="68" height="36" rx="10" fill="#0fbcb0"/>
  <text x="182" y="31" text-anchor="middle" fill="#ffffff" font-size="12" font-weight="700">道具</text>
</svg>
```

### SVG 模板 — 像素风标签徽章
```xml
<svg width="80" height="24" xmlns="http://www.w3.org/2000/svg">
  <rect width="80" height="24" rx="4" fill="#ffd02f"/>
  <rect x="0" y="0" width="80" height="24" rx="4" fill="none" stroke="#23251d" stroke-width="2"/>
  <text x="40" y="16" text-anchor="middle" fill="#23251d"
        font-size="10" font-family="monospace" font-weight="700">NEW!</text>
</svg>
```
