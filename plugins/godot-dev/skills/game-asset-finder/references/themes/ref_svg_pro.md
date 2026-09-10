# SVG 主题：企业/专业/极简风 (pro)

## 十、专业/极简风 `pro`

**参考品牌**：IBM, Apple, Tesla, BMW, Coinbase, Linear, Vercel, Expo

### 调色板
```
背景：    #ffffff / #000000
主色：    #0f62fe（IBM蓝）/ #0066cc（苹果蓝）/ #3e6ae1（特斯拉蓝）/ #171717
文字：    #161616 / #000000 / #ffffff
圆角：    0px（Tesla/BMW）或 8px（中等）
```

### 按钮造型
- **矩形0圆角**：Tesla/BMW，工程美学
- **标准 pill**：Apple/Coinbase，含蓄圆润

### SVG 模板 — IBM 蓝矩形按钮（0圆角）
```xml
<svg width="160" height="44" xmlns="http://www.w3.org/2000/svg">
  <rect width="160" height="44" fill="#ffffff"/>
  <rect x="8" y="8" width="144" height="28" rx="0" fill="#0f62fe"/>
  <text x="80" y="26" text-anchor="middle" fill="#ffffff"
        font-size="13" font-family="'IBM Plex Sans',system-ui" font-weight="300" letter-spacing="0.5">确认</text>
</svg>
```
