# 通用 SVG 组件模板

> 与主题无关的通用游戏 UI 组件，可直接用于任意风格，通过修改颜色参数适配各主题。
> 包含：血条/HP Bar、技能 CD 图标、地图 Pin 标记、弹窗面板框架。

---

## 血条/HP Bar（通用，可换色）

```xml
<svg width="220" height="32" xmlns="http://www.w3.org/2000/svg">
  <!-- 外框 -->
  <rect width="220" height="18" y="7" rx="9" fill="#1a1a1a" stroke="rgba(255,255,255,0.1)" stroke-width="1"/>
  <!-- 血量（改 width 和 fill 即可） -->
  <rect x="2" width="154" height="14" y="9" rx="7" fill="#da291c"/>
  <!-- 高光 -->
  <rect x="2" width="154" height="4" y="9" rx="7" fill="rgba(255,255,255,0.15)"/>
  <!-- 标签 -->
  <text x="4" y="5" fill="#ffffff" font-size="9" font-family="system-ui" font-weight="700">HP</text>
  <text x="216" y="5" text-anchor="end" fill="#ffffff" font-size="9" font-family="system-ui">154/220</text>
</svg>
```

**定制参数：**
- `width="154"` → 血量百分比对应宽度（满血=216）
- `fill="#da291c"` → 替换为各主题主色（赛博用 `#5e6ad2`，暖色用 `#cc785c` 等）
- 外框 `rx="9"` → 0 改为方形（luxury/pro 风），保持 9 为圆形（warm/nature 风）

---

## 圆形技能 CD 图标（通用）

```xml
<svg width="52" height="52" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="circ"><circle cx="26" cy="26" r="24"/></clipPath>
  </defs>
  <!-- 底层 -->
  <circle cx="26" cy="26" r="24" fill="#1a1a1a" stroke="#333" stroke-width="1.5"/>
  <!-- CD 遮罩（扇形，可用 JS 动画） -->
  <circle cx="26" cy="26" r="18" fill="none" stroke="#5e6ad2" stroke-width="6"
          stroke-dasharray="70 43" stroke-dashoffset="0" transform="rotate(-90 26 26)"/>
  <!-- CD 数字 -->
  <text x="26" y="31" text-anchor="middle" fill="#ffffff"
        font-size="14" font-family="system-ui" font-weight="700">3</text>
</svg>
```

**定制参数：**
- `stroke="#5e6ad2"` → 圆环颜色，替换为主题主色
- `stroke-dasharray="70 43"` → 圆周长约 113，dasharray 前值控制已冷却弧长（70/113 ≈ 62% 已冷却）
- CD 数字改为 `0` 表示可用，`>0` 表示冷却剩余秒数
- 可在圆形内叠加技能图标 `<image>` 或简单路径

---

## 地图标记 Pin（通用）

```xml
<svg width="32" height="40" xmlns="http://www.w3.org/2000/svg">
  <path d="M16 2 C8.268 2 2 8.268 2 16 C2 26 16 38 16 38 C16 38 30 26 30 16 C30 8.268 23.732 2 16 2Z"
        fill="#da291c" stroke="#ffffff" stroke-width="1.5"/>
  <circle cx="16" cy="16" r="5" fill="#ffffff"/>
</svg>
```

**定制参数：**
- `fill="#da291c"` → Pin 颜色（敌方红、友方蓝、目标金等）
- `stroke="#ffffff"` → 描边，深色背景下用白色，浅色背景下用深色
- 内圆 `r="5"` 可替换为图标路径（如宝剑、星形等）

**颜色约定建议：**
| 类型 | 颜色 |
|------|------|
| 敌方 | `#da291c` |
| 友方 | `#0070d1` |
| 任务目标 | `#ffc000` |
| 兴趣点 | `#3ecf8e` |

---

## 通用弹窗面板框架（可换主题色）

```xml
<svg width="300" height="180" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="panelShadow" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="4" stdDeviation="12" flood-color="rgba(0,0,0,0.5)"/>
    </filter>
  </defs>
  <!-- 面板背景 -->
  <rect width="300" height="180" rx="12" fill="#181818" filter="url(#panelShadow)"/>
  <!-- 顶部标题栏 -->
  <rect width="300" height="40" rx="12" fill="#222222"/>
  <rect width="300" height="12" y="28" fill="#222222"/>
  <!-- 标题文字 -->
  <text x="16" y="26" fill="#ffffff" font-size="14" font-family="system-ui" font-weight="600">游戏暂停</text>
  <!-- 关闭按钮 -->
  <circle cx="278" cy="20" r="10" fill="#333333"/>
  <line x1="273" y1="15" x2="283" y2="25" stroke="#999" stroke-width="1.5" stroke-linecap="round"/>
  <line x1="283" y1="15" x2="273" y2="25" stroke="#999" stroke-width="1.5" stroke-linecap="round"/>
  <!-- 内容区域占位 -->
  <rect x="16" y="56" width="268" height="1" fill="rgba(255,255,255,0.08)"/>
</svg>
```

**定制参数：**
- `fill="#181818"` / `fill="#222222"` → 面板/标题栏背景，随主题调整（浅色主题改为 `#ffffff` / `#f5f5f5`）
- `rx="12"` → 圆角，luxury/pro 改为 `rx="0"` 锐角，playful 改为 `rx="16"` 更圆润
- 标题栏高度 40px 固定，内容区从 y=56 开始（含分割线）
- 可在内容区继续添加按钮、文本、图标等子元素

---

## 主题适配速查

| 通用组件 | cyber | luxury | warm | playful | pro |
|---------|-------|--------|------|---------|-----|
| 血条颜色 | `#5e6ad2` | `#da291c` | `#cc785c` | `#ffd02f` | `#0f62fe` |
| CD图标颜色 | `#5e6ad2` | `#ffc000` | `#f7a501` | `#4262ff` | `#0f62fe` |
| 面板圆角 | `rx="4"` | `rx="0"` | `rx="12"` | `rx="16"` | `rx="0"` |
| 面板背景 | `#181818` | `#181818` | `#faf9f5` | `#ffffff` | `#ffffff` |

---

*恢复自 session 39678401（ref_svg_themes.md 原文件第 502~562 行）。*
*适用：game-asset-finder skill，SVG UI 元素生成时的通用组件参考。*
