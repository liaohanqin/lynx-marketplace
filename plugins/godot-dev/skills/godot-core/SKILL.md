---
name: godot-core
description: >
  Godot 游戏开发的统一入口。当用户提出「做游戏 / 开发游戏 / 加玩法 / 写 GDScript /
  改场景 / 改节点 / 做关卡 / 做 UI / 做角色 / 做敌人 / 做菜单 / 做 2D / 做 3D」
  等请求时激活。负责判断场景（新建/修改/重连），把控制权分派给对应的领域 skill，
  并通过 tomyud1/godot-mcp 的 MCP 工具实际操作 Godot 编辑器。
---

# Godot 开发统一入口

本 skill 是 Godot 开发的调度入口。它**只负责判断意图 + 分派**，具体的领域知识
（玩家控制、UI、存档、玩法设计等）由对应的子 skill 提供。

## 工具链约定（tomyud1/godot-mcp）

本项目通过 **tomyud1/godot-mcp** 的 MCP 工具驱动 Godot 编辑器，与官方
`anengyuki/Godot-mcp`（`build_godot_scene` 单工具、9080 端口、腾讯后端）**不是
同一套**。注意区别：

- MCP server 由 `npx godot-mcp-server` 启动，Godot 插件通过 WebSocket 连
  `ws://127.0.0.1:6505`（不是 9080）。
- 工具是**细粒度的 42 个工具**，分 6 类：文件操作、场景操作、脚本操作、项目工具、
  资产生成、可视化。没有 `build_godot_scene` 这种"一次性传整棵树"的工具。
- 单实例限制：一个 MCP server 同时只连一个 Godot 编辑器实例，不要同时开两个项目。

常用工具（按需查阅 MCP 工具列表确认确切名称和参数）：

| 类别 | 工具示例 |
|------|----------|
| 场景操作 | 创建场景、添加/移除/移动节点、设置属性、挂脚本、设置碰撞/贴图 |
| 脚本操作 | 应用代码编辑、校验语法、重命名/移动文件并更新引用 |
| 项目工具 | 运行/停止场景、查询 ClassDB、读取错误、项目设置、场景树 dump |
| 文件操作 | 浏览目录、读文件、搜索项目、创建脚本 |
| 资产生成 | 从 SVG 生成 2D 精灵 |

## 意图判别（不要反问用户，按优先级判定）

把用户原话做关键词匹配：

| 意图 | 触发词 |
|------|--------|
| `new_game` | 「再来一个 / 新游戏 / 换一个游戏 / another game」 |
| `make_game` | 「做一个 X / 帮我做个 X / make a X / build a X」（X 是游戏类型） |
| `modify_game` | 「加 / 改 / 删 / 优化 / 调整 / 修复」+ 节点/场景/脚本/UI/角色/敌人/关卡/菜单 |

判定优先级：
1. 当前工作区无 `project.godot`（或用户明确说新建）→ `make_game`
2. 已有 `project.godot` 且出现 `new_game` 词 → `new_game`
3. 其他 → `modify_game`

## 场景处理

### make_game / new_game（新建项目）

1. 用 MCP 文件/项目工具在目标目录创建 `project.godot` 和基本目录
   （`scenes/ scripts/ assets/ data/ docs/`）。
2. 提示用户用 Godot 编辑器打开项目，并启用 Godot MCP 插件（GUI 操作，agent 无法代做）。
3. 根据用户需求分派到对应领域 skill（如 `player-system`、`ui-system`）生成内容。

### modify_game（修改现有项目）

1. 用 MCP 场景/脚本工具实际操作编辑器：
   - 改场景：用场景操作工具（create/add/set property），**不要**手写 `.tscn` 文本
   - 改脚本：用脚本操作工具或直接读写 `.gd` 文件
   - 改策划/文档：直接读写 `docs/`、`data/`
   - 二进制资源：复制到 `assets/`，由 Godot 编辑器自动 reimport
2. 完成后用 MCP 的「读取错误」工具确认无报错，必要时自动修复。

## Godot 4 路径与类型约定（写 MCP 工具参数时遵守）

| 类型 | 格式 | 示例 |
|------|------|------|
| 资源路径 | `res://...` | `res://scenes/main.tscn` |
| 节点类型 | Godot 4 类名 | `Node2D` / `CharacterBody2D` / `Control` |
| 脚本扩展名 | `.gd` | `res://scripts/player.gd` |
| 场景扩展名 | `.tscn`（文本格式） | `res://scenes/main.tscn` |
| Vector2/Vector3 | 数组 | `[100, 200]` / `[1, 2, 3]` |
| Color | RGBA 数组 0-1 | `[1, 0.5, 0.5, 1]` |
| 旋转单位 | 弧度 | `1.5708` |

## 严禁行为

- 不要为「改场景」手写 `.tscn` 文本，用 MCP 场景工具。
- 不要在 MCP 连接失败时反复重试同一工具——先定位连接问题（见下）。
- 不要凭空发明 MCP 工具名，不确定时先查工具列表。

## MCP 连接异常处理

调用 MCP 工具收到「工具不存在 / connection refused / WebSocket」类错误时：
- 检查 `npx godot-mcp-server` 是否在运行（agent-shell 启动时会自动拉起）
- 检查 Godot 编辑器顶部工具栏是否有 `MCP:` 状态（绿色 = 已连接）
- 让用户确认 Godot MCP 插件已在 Project Settings 启用
