---
name: translate
description: Use when 用户要求把 EPUB 电子书翻译成中文或中英对照版本，或需要校验、补漏已生成的双语 EPUB。适用于需保留原书图片、代码块、排版样式，且要求段落级中英交替对照的场景。
---

# EPUB 中英双语化

把 EPUB 电子书转成**段落级中英对照**版本：每个英文块之后紧跟一个中文块，原书 HTML 结构、图片、代码、CSS 全部保留。

## 核心原则

**原 HTML 一个字节都不改，只在英文块之后"追加"中文块。** 这保证任何一步出错都不会破坏原书，且随时可从原书重来。

## 前置检查（必做）

```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/verify.py --epub "<源文件>"   # 确认源是有效 zip
```

依赖：Python 3.8+、`lxml`。用 venv 装，别污染系统 pip：
```bash
python3 -m venv --system-site-packages /tmp/epub-venv   # lxml 常已存在，可零新增依赖
```

## 工作流

```bash
S=${CODEBUDDY_SKILL_DIR}/scripts

# 1) 试跑：先跑 1 个文件的前 6 块，验证整条管线
python3 $S/translate.py --src "in.epub" --out /tmp/try.epub \
        --cache /tmp/try_cache.json --limit-files 1 --limit-blocks 6

# 2) 全量（缓存命中，试跑的块不会重译）
python3 $S/translate.py --src "in.epub" --out "out.epub" \
        --cache /tmp/cache.json --log /tmp/run.log --workers 6

# 3) 兜底校验：正常应为 0（主脚本已用占位符就地保留行内代码）
python3 $S/fix_codes.py --src "out.epub" --out /tmp/fixed.epub

# 4) 校验（含"行内代码原文是否保留在译文中"）
python3 $S/verify.py --epub "out.epub" --source "in.epub"
```

常用参数（完整列表 `--help`）：

| 参数 | 用途 |
|---|---|
| `--files A.xhtml,B.xhtml` | 只处理指定文件（按章精修） |
| `--retranslate` | 先清除旧译文再重译（配合 `--files` 精修单章） |
| `--exclude k1,k2` | 排除文件名含关键词的条目，默认已排除 cover/nav/toc/index |
| `--model` | 翻译模型，默认 `hy3-ioa` |
| `--workers` | 并发数，默认 6 |

## 五个必踩的坑

完整说明与实测数据见 `references/pitfalls.md`。这里只列必须记住的：

1. **必须先量吞吐再选模型。** 同一批文本，`hy3-ioa` 6 并发约 300 ch/s（全书 40 分钟），
   `hy4-preview-ioa` 单并发仅 9.2 ch/s（全书 22 小时），相差 10 倍以上。先跑小样本量出速度，
   把耗时报给用户再动手。

2. **接口必须 `stream:true`。** CodeBuddy 平台 LLM 的非流式请求会返回
   `code 11101 Non-stream chat request is currently not supported`。
   Google Translate 在本网络被屏蔽（返回 `Sorry...` 拦截页），不要选它。

3. **行内 `<code>` 必须用占位符送译，不能当纯文本塞给 LLM。** 拍平成纯文本后代码会被当作
   "举例说明"整段吞掉（实测全书漏 1545 处）。主脚本已用 `⟦N⟧` 占位符：送译前替换、
   译完再替换回原文 —— 代码因此**留在译文中它该在的位置**。译文若丢失占位符会被判失败并重译。

   `fix_codes.py` 只是兜底：它把原文**追加到译文末尾**，脱离上下文、破坏译文，
   不能当主方案。实测对比（同一章）：追加法 77 处被挪到末尾，占位符法 0 处。

4. **容器块不能整体跳过。** 含子块的 `<li>`（列表导语 + 内嵌 `<p>`）若为防止重复而整体跳过，
   其直系文本会漏译。正确做法：只取容器**直系文本**单独翻译，译文插在第一个子块之前。

5. **跨设备移动会崩。** `/tmp` 与 `/mnt/c` 之间 `os.replace` 抛
   `OSError: [Errno 18] Invalid cross-device link`，用 `shutil.move`。

## 进度汇报铁律

**不许凭印象声称"后台任务在跑"。** 报进度前必须读实际证据（日志行数、缓存条数、输出文件是否存在）。

启动后台任务后立即验证一次进程/日志在推进，并报具体数字（`1154/2423 块，失败 0`），
而不是"正在运行中"。上一轮曾出现脚本 0 字节、任务从未运行却回复"后台全力运行"的事故。

## 常见错误

| 现象 | 原因 | 修复 |
|---|---|---|
| 阅读器打不开 | `mimetype` 不是首条目或被压缩 | 脚本已处理；勿手改打包逻辑 |
| 译文统计虚高、报"缺失译文" | 校验时把译文块（含 Godot 等 ASCII 术语）也当英文块统计 | 统计时排除 `class="cn"`/`"cn-h"` |
| 校验口径与翻译漂移（误报缺失） | 校验脚本自己重写了块筛选逻辑 | 必须复用 `collect_blocks()`，不重写 |
| 块全部需要重译、缓存不命中 | 提取文本时把 `<code>` 整段跳过，缓存键与现在不同 | 用占位符版本 `extract_text()`；`<code>` 判断须先于 `SKIP_SUBTREE` |
| 译文块重复叠加 | 精修时未清除旧译文 | 加 `--retranslate` |
| 术语前后不一致 | 跨批次翻译 | 提示词内置术语表；残余不一致无法完全消除 |
| 中文字体不显示 | 依赖阅读器系统 CJK 字体回退 | 已注入 `font-family` 回退链，属预期 |

## 参考

- `references/pitfalls.md` —— 全部踩坑的实测数据与根因分析
- `scripts/common.py` —— 块解析与打包的共享实现
