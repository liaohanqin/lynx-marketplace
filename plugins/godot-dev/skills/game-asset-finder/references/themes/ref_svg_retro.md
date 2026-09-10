# SVG 主题：复古/Y2K风 (retro)

## 七、复古/Y2K风 `retro`

**参考品牌**：Nintendo-2001, Dell-1996, Miro(部分)

### 调色板
```
背景：    #7a8aba（金属蓝）/ #ffffff（白纸）/ #000000（黑框）
强调：    #e60012（任天堂红）/ #f68d1f（琥珀橙）/ #ecab37（金色）
铬色：    #3d4f97（铬靛）/ #dedede（铂金灰）/ #21242e（碳黑）
色块：    多彩色带（sage/salmon/periwinkle/lime）
```

### 按钮造型
- **斜面3D按钮**：亮边 + 暗边模拟凸起，square corners
- **彩色色带卡片**：Dell 风格实色背景区块

### SVG 模板 — 斜面3D按钮（Nintendo 风）
```xml
<svg width="120" height="36" xmlns="http://www.w3.org/2000/svg">
  <!-- 阴影面 -->
  <rect x="3" y="3" width="117" height="33" rx="2" fill="#3d4f97"/>
  <!-- 主体 -->
  <rect width="117" height="33" rx="2" fill="#9fbee7"/>
  <!-- 高光边 -->
  <line x1="1" y1="1" x2="116" y2="1" stroke="#c0d5e6" stroke-width="1.5"/>
  <line x1="1" y1="1" x2="1" y2="32" stroke="#c0d5e6" stroke-width="1.5"/>
  <text x="58" y="21" text-anchor="middle" fill="#21242e"
        font-size="11" font-family="Arial" font-weight="700">START GAME</text>
</svg>
```
