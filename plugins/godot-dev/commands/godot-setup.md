---
description: "安装 / 配置 / 排障 Godot MCP 后端（tomyud1/godot-mcp，纯本地 6505）"
argument-hint: ""
---

# /godot-dev:godot-setup

显式触发 [godot-setup](../skills/godot-setup/SKILL.md) Skill，处理 Godot MCP 后端的
安装、配置与连接排障。

> 后端只有一套：tomyud1/godot-mcp（纯本地，WebSocket 6505，无腾讯后端、无 API key）。
> 遇到「安装 Godot MCP 插件 / 配置 MCP / MCP 连不上」等请求时，直接按
> godot-setup Skill 执行，**不要**列出多套后端、**不要**反问用户装哪套。

## 行为

1. 全权委托给 `godot-setup` Skill，按其流程执行：
   - 就绪判断（插件文件 / 启用 / .mcp.json 注册 / 状态灯颜色）
   - 区分 agent-shell（自动注入，无需手配）与普通 CodeBuddy（需手配 .mcp.json）两条路径
   - 给出安装步骤或排障建议
2. 把 Skill 的结论原样回显给用户。

## 失败处理

若 MCP 工具报「连接失败 / tool not found」，按 godot-setup Skill 的排障表定位，
不要让用户反复重试同一操作。
