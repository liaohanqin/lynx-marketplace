# SVG 主题：编辑/赛博媒体风 (editorial)

## 九、编辑/赛博媒体风 `editorial`

**参考品牌**：TheVerge, Wired, Sanity, OpenCode, Resend

### 调色板
```
背景：    #131313（近黑）/ #0b0b0b
强调：    #3cffd0（薄荷）/ #5200ff（紫外）/ #f36458（珊瑚红）
文字：    #ffffff / #949494
边框：    1px 主色实心描边（无阴影）
```

### 按钮造型
- **大圆角彩色块**：20~40px 圆角，高饱和填充
- **无阴影，纯描边分层**

### SVG 模板 — TheVerge 薄荷按钮
```xml
<svg width="160" height="44" xmlns="http://www.w3.org/2000/svg">
  <rect width="160" height="44" rx="8" fill="#131313"/>
  <rect x="4" y="4" width="152" height="36" rx="20" fill="#3cffd0"/>
  <text x="80" y="26" text-anchor="middle" fill="#000000"
        font-size="13" font-family="system-ui" font-weight="700">读取存档</text>
</svg>
```
