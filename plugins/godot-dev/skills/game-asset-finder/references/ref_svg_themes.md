# SVG UI 设计主题参考

> 从 70+ 个品牌设计系统中提炼，用于指导游戏 UI SVG 元素的生成。
> 按游戏风格分类，每个主题提供：调色板、按钮造型、特效、SVG 代码模板。

---

## 主题速查表

| 主题 | 代号 | 背景 | 主色 | 适用场景 |
|------|------|------|------|---------|
| 赛博朋克/科技 | `cyber` | #010102~#0f0f0f | 电黄/薰衣草蓝/电绿 | 科幻、黑客、未来世界 |
| 奢华黑暗 | `luxury` | #000000~#181818 | 金/红/白 | 赛车、格斗、高端 RPG |
| 自然清新 | `nature` | #ffffff~#fafaf0 | 翠绿/青柠/珊瑚 | 休闲、农场、益智 |
| 宇宙史诗 | `space` | #000000~#010120 | 橙/洋红/白 | 太空、冒险、策略 |
| 暖色温馨 | `warm` | 奶油#faf9f5~#fff8e0 | 橙/棕/珊瑚 | 解谜、文字、叙事 |
| 游乐/像素 | `playful` | #ffffff~#eeefe9 | 黄/紫/多彩 | 平台跳跃、像素、卡通 |
| 企业/专业 | `pro` | #ffffff | 蓝/黑 | 棋类、策略、商业 |
| 复古/8位 | `retro` | 金属蓝#7a8aba | 琥珀/红/铬 | 复古像素、Y2K |
| 电影沉浸 | `cinematic` | #000000~#030303 | 白/冷灰 | 动作、恐怖、叙事 |
| 编辑/媒体 | `editorial` | #131313~#000000 | 薄荷/紫外 | 赛博新闻、策略 |

---

## 主题详细参考

@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_cyber.md
@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_luxury.md
@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_nature.md
@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_space.md
@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_warm.md
@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_playful.md
@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_pro.md
@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_retro.md
@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_cinematic.md
@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_editorial.md

---

## 通用 UI 组件模板（跨主题）

@${CODEBUDDY_SKILL_DIR}/references/themes/ref_svg_common.md

---

## 主题选择建议

| 游戏类型 | 推荐主题 | 备选 |
|---------|---------|------|
| 科幻/黑客/未来 | `cyber` | `editorial` |
| 赛车/格斗/高端 RPG | `luxury` | `cinematic` |
| 太空冒险/策略 | `space` | `cyber` |
| 休闲/农场/益智 | `nature` | `warm` |
| 解谜/文字/叙事 | `warm` | `editorial` |
| 平台跳跃/像素/卡通 | `playful` | `retro` |
| 复古/FC/Y2K | `retro` | `playful` |
| 棋类/商业模拟 | `pro` | `warm` |
| 电影级沉浸 | `cinematic` | `luxury` |
| 动作赛博朋克媒体 | `editorial` | `cyber` |

---

*数据来源：70+ 品牌 DESIGN.md，包括 Apple, Spotify, Stripe, Linear, Ferrari, PlayStation, Nintendo 等。*
*用于：game-asset-finder skill SVG 生成路径的设计参考。*
