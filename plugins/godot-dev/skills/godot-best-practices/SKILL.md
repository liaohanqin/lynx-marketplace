---
name: godot-best-practices
description: >
  Godot 架构与设计模式指导，提炼自《Godot 4 Best Practices》。当用户询问
  「架构 / 设计模式 / SOLID / 代码结构 / 场景组织 / 组件 / 状态机 / 事件驱动 /
  数据驱动 / 依赖注入 / 单例 / 工厂 / 命令模式 / 分层架构 / 重构 / 反模式 /
  God class / 可扩展 / 可维护」等架构与代码设计问题时激活。讲原理、权衡与反模式，
  与 code-generator（给模板）互补。只读知识库，不直接改代码。
allowed-tools: Read
---

# Godot 架构与设计模式指导

面向**中级开发者**，解决「从能跑的原型走向可扩展、可维护的生产级项目」这一核心挑战。
本书不教 GDScript 语法或编辑器操作，而是教**何时该用什么架构、为什么、有什么坑**。

## 贯穿全书的黄金法则

1. **Call Down, Signal Up, Event Out** — 父节点向下调用子节点方法，子节点向上发信号，跨系统通信走事件总线
2. **组合优于继承** — 能用组件/子节点拆解的行为，不要塞进深层继承
3. **逻辑与表现分离** — 数据/领域逻辑不依赖 UI、音频等表现层
4. **依赖抽象不依赖细节** — 用信号和 `@export` 注入解耦，别用 `get_node("../xxx")` 硬编码路径
5. **原则是工具不是铁律** — 小原型先做出可玩版本，别过度设计

## 参考文档索引

按主题查阅对应 reference 文件：

| 主题 | 何时查阅 | 文件 |
|------|---------|------|
| SOLID 五原则 | 脚本职责混乱、继承关系设计、依赖解耦、feature 目录结构 | `${CODEBUDDY_SKILL_DIR}/references/solid-principles.md` |
| 场景与节点 | 场景 vs 脚本决策、场景模块化组织、何时用 Resource 而非节点 | `${CODEBUDDY_SKILL_DIR}/references/scenes-and-nodes.md` |
| 设计模式 | Autoload/单例、事件驱动、状态/策略、组件、工厂/建造者、命令/服务 | `${CODEBUDDY_SKILL_DIR}/references/design-patterns.md` |
| 数据与架构 | 数据驱动设计、逻辑与配置分离、分层架构、God class 重构 | `${CODEBUDDY_SKILL_DIR}/references/data-and-architecture.md` |

## 每个 reference 的统一结构

每个原则/模式按五段组织：
- **核心原则** — 一句话说明
- **适用场景** — 何时用
- **反模式** — 错误做法 + 为什么错
- **正确做法** — 精简 GDScript 示例
- **权衡与陷阱** — 何时不用、代价

## 与其它 skill 的关系

- **`code-generator`**：给具体代码模板（单例/组件/状态机骨架）；本 skill 讲这些模式背后的**原理、权衡、适用场景**。用户要「模板」查 code-generator，要「为什么这么设计 / 该不该用」查本 skill。
- **`godot-core`**：统一入口，负责意图分派；当意图是「架构/设计模式/代码结构咨询」时应分派到本 skill。
- **`gameplay-design`**：玩法策划层面；本 skill 是代码架构层面。

## 使用方式

1. 判断用户问题属于哪个主题（SOLID / 场景节点 / 设计模式 / 数据架构）
2. 用 Read 工具读取对应 reference 文件（用上表的 `${CODEBUDDY_SKILL_DIR}` 路径）
3. 结合用户的具体代码/场景，给出针对性建议，引用 reference 中的原则与权衡
4. 必要时建议用户用 code-generator 生成符合该架构的代码模板
