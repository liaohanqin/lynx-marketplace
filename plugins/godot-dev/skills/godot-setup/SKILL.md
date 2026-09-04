---
name: godot-setup
description: >
  Godot MCP 后端的安装与连接排障。当用户要求「安装 Godot MCP / 部署 MCP /
  配置 MCP / MCP 连不上 / Godot MCP 插件安装」时激活。明确后端是 tomyud1/godot-mcp
  （纯本地，6505 端口），并给出就绪判断与安装步骤，避免在「装哪套后端」上反问用户。
---

# Godot MCP 后端安装与连接排障

本 skill 负责 Godot MCP **后端（MCP server）** 的安装、配置和连接判断。

## 先明确：后端只有一套

本项目使用的 Godot MCP 后端是 **tomyud1/godot-mcp**（纯本地开源，MIT）：

- 仓库：`https://github.com/tomyud1/godot-mcp`
- MCP server：Node.js 包 `godot-mcp-server`，通过 `npx -y godot-mcp-server` 启动
- Godot 插件：仓库内 `addons/godot_mcp/`，通过 WebSocket 连 `ws://127.0.0.1:6505`
- **无外部后端、无 API key、无腾讯后端**（区别于 `anengyuki/Godot-mcp` 的 9080 + GODOT_API_KEY）

**不要**在「装哪套后端」上反问用户（如 A/B/C 选择）。默认就是 tomyud1/godot-mcp。
除非用户明确提到「官方插件」「腾讯后端」「anengyuki」，否则一律按 tomyud1 处理。

## 就绪判断（先判断，再决定要不要装）

按顺序检查，任一不满足就对应处理：

1. **Godot 插件是否在项目里**：`<project>/addons/godot_mcp/plugin.cfg` 是否存在。
2. **插件是否启用**：`<project>/project.godot` 是否含
   `[editor_plugins]` + `enabled=...godot_mcp...`。
3. **MCP server 是否注册**：`.mcp.json`（或 `.codebuddy/.mcp.json`）里是否有
   `godot` 服务器条目。
4. **Godot 编辑器顶部工具栏**是否有 `MCP:` 状态灯：
   - 黄色 `MCP: Connecting...` / 红色 `MCP: Disconnected` → server 没跑或没连上
   - 橙色 `MCP: No Agent` → server 已就绪，等 agent 连
   - 绿色 `MCP: Agent Active` → 全链路通

## 两条使用路径（关键区别）

### 路径 A：在 agent-shell 里用（推荐）

agent-shell 的 `agent-shell-godot`（`agent-shell-godot-start-agent`）会通过
ACP `:mcp-servers` **自动注入并拉起** tomyud1/godot-mcp，**无需手动配 `.mcp.json`**。

此时你只需要：
1. 确认 Godot 插件已复制到项目 `addons/godot_mcp/` 并在编辑器里启用。
2. 确认编辑器顶部 `MCP:` 灯变绿（或至少橙色）。

**不要**在 agent-shell 场景下再去改 `.mcp.json` 或手动 `npx godot-mcp-server`——
那是重复且会冲突的。

### 路径 B：在普通 CodeBuddy 会话里用（无 agent-shell）

需要手动配后端：

1. **装 Godot 插件**（GUI 部分无法代做，需用户操作）：
   - 复制 `addons/godot_mcp/` 到项目 `addons/`
   - `project.godot` 追加 `[editor_plugins]` + `enabled=PackedStringArray("godot_mcp")`
   - 用户去 Project → Project Settings → Plugins 勾选并重启编辑器

2. **在 `.mcp.json` 注册 server**（stdio）：
   ```json
   {
     "mcpServers": {
       "godot": {
         "command": "npx",
         "args": ["-y", "godot-mcp-server"]
       }
     }
   }
   ```

3. **重启 CodeBuddy** 让其拉起 server，Godot 顶部灯应变绿。

## 常见排障

| 症状 | 原因 | 处理 |
|------|------|------|
| 灯一直是红色 Disconnected | server 没跑 | 确认 `.mcp.json` 有 godot 条目，重启 CodeBuddy |
| 灯是橙色 No Agent | server 就绪但无 agent | 正常，等 agent 用 MCP 工具即变绿 |
| 调用工具报 tool not found | 插件版本旧 | 更新 addons/godot_mcp 到最新 |
| 端口冲突 | 同时开了两个 Godot 编辑器 | 关掉多余实例（单实例限制） |

## 注意

- tomyud1 单实例：一个 MCP server 只连一个 Godot 编辑器。
- 本 skill 只处理**后端**；游戏内容开发交给 `godot-core` 及其他领域 skill。
