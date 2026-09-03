---
name: code-generator
description: >
  GDScript 代码生成规范。生成 Godot 脚本时遵守：命名约定、文件组织、
  常用模板（单例/实体/组件/状态机/UI控制器/系统/数据类）。
  当用户要求「生成代码 / 创建脚本 / 写一个 / 实现某功能 / 控制器 / 管理器」时激活。
---

# GDScript 代码生成规范

根据模板和需求生成规范的 GDScript 代码。

## 命名约定

| 类型 | 命名方式 | 示例 |
|------|----------|------|
| 类名 | PascalCase | `PlayerController`, `GameManager` |
| 函数名 | snake_case | `get_health()`, `apply_damage()` |
| 变量名 | snake_case | `max_health`, `current_speed` |
| 常量 | UPPER_SNAKE_CASE | `MAX_SPEED`, `DEFAULT_HEALTH` |
| 信号 | snake_case | `health_changed`, `died` |
| 枚举 | PascalCase(类型) + UPPER_SNAKE_CASE(值) | `enum State { IDLE, RUNNING }` |

## 文件组织模板

```gdscript
## 类描述（文档注释）
##
## @author AI Generated
## @version 1.0.0
class_name ClassName
extends BaseClass

# region 信号
signal signal_name(param: Type)
# endregion

# region 常量
const MAX_VALUE: int = 100
# endregion

# region 导出变量
@export var exported_var: Type
@export_group("Group Name")
@export var grouped_var: Type
# endregion

# region 公共变量
var public_var: Type
# endregion

# region 私有变量
var _private_var: Type
# endregion

# region 生命周期方法
func _ready() -> void:
    pass

func _process(delta: float) -> void:
    pass

func _physics_process(delta: float) -> void:
    pass
# endregion

# region 公共方法
func public_method() -> ReturnType:
    pass
# endregion

# region 私有方法
func _private_method() -> void:
    pass
# endregion
```

## 模板类型

### 1. 单例模板 (Singleton)

用于全局管理器（GameManager、AudioManager 等），通过 Autoload 加载。

```gdscript
class_name {{CLASS_NAME}}
extends Node

# region 信号
{{SIGNALS}}
# endregion

# region 常量
{{CONSTANTS}}
# endregion

# region 私有变量
{{PRIVATE_VARS}}
# endregion

func _ready() -> void:
    _initialize()

func _initialize() -> void:
    {{INIT_CONTENT}}
# endregion

# region 公共 API
{{PUBLIC_METHODS}}
# endregion

# region 内部方法
{{PRIVATE_METHODS}}
# endregion
```

### 2. 实体模板 (Entity)

用于游戏实体（Player、Enemy 等）。核心：`current_health` 用 setter 做钳位 + 信号。

```gdscript
class_name {{CLASS_NAME}}
extends {{BASE_CLASS}}

signal died
signal health_changed(old_value: int, new_value: int)

@export_group("Stats")
@export var max_health: int = 100
@export var move_speed: float = 200.0

var current_health: int:
    set(value):
        var old = current_health
        current_health = clampi(value, 0, max_health)
        health_changed.emit(old, current_health)
        if current_health <= 0:
            _die()

var is_alive: bool:
    get: return current_health > 0

func _ready() -> void:
    current_health = max_health

func take_damage(amount: int, source: Node = null) -> void:
    if not is_alive:
        return
    current_health -= amount

func heal(amount: int) -> void:
    current_health += amount

func _die() -> void:
    died.emit()
```

### 3. 组件模板 (Component)

用于可复用功能组件，附加到实体节点上。

```gdscript
class_name {{CLASS_NAME}}
extends Node

@export var enabled: bool = true

var _owner_entity: Node

func _ready() -> void:
    _owner_entity = get_parent()
    if not _owner_entity:
        push_error("{{CLASS_NAME}} must be a child of an entity node")
        return
    _initialize()

func _process(delta: float) -> void:
    if not enabled:
        return
    {{PROCESS_CONTENT}}

func _initialize() -> void:
    {{INIT_CONTENT}}
```

### 4. 状态机状态模板 (State)

用于状态机中的单个状态。配合 StateMachine 使用（见 player-system）。

```gdscript
class_name {{CLASS_NAME}}
extends State

func enter() -> void:
    {{ENTER_CONTENT}}

func exit() -> void:
    {{EXIT_CONTENT}}

func update(delta: float) -> void:
    {{UPDATE_CONTENT}}

func physics_update(delta: float) -> void:
    {{PHYSICS_UPDATE_CONTENT}}

func handle_input(event: InputEvent) -> void:
    {{INPUT_CONTENT}}

func get_transition() -> StringName:
    {{TRANSITION_CHECKS}}
    return &""
```

### 5. UI 控制器模板 (UI Controller)

```gdscript
class_name {{CLASS_NAME}}
extends Control

signal opened
signal closed

@onready var {{NODE_REFS}}

func _ready() -> void:
    _setup_ui()
    _connect_signals()

func _setup_ui() -> void:
    {{SETUP_UI}}

func _connect_signals() -> void:
    {{CONNECT_SIGNALS}}

func open() -> void:
    show()
    opened.emit()

func close() -> void:
    hide()
    closed.emit()

func refresh() -> void:
    {{REFRESH_CONTENT}}
```

### 6. 系统模板 (System)

用于游戏系统（战斗、背包等）。

```gdscript
class_name {{CLASS_NAME}}
extends Node

signal {{SIGNALS}}

const {{CONSTANTS}}

var {{DATA_STORAGE}}

func _ready() -> void:
    _load_config()
    _initialize()

func _load_config() -> void:
    {{LOAD_CONFIG}}

func _initialize() -> void:
    {{INIT_CONTENT}}

# region 公共 API
{{PUBLIC_API}}
# endregion

# region 数据持久化
func save_data() -> Dictionary:
    {{SAVE_DATA}}
    return {}

func load_data(data: Dictionary) -> void:
    {{LOAD_DATA}}
# endregion
```

### 7. 数据类模板 (Data Class)

用于定义数据结构，继承 Resource。

```gdscript
class_name {{CLASS_NAME}}
extends Resource

@export {{PROPERTIES}}

func to_dict() -> Dictionary:
    return {
        {{TO_DICT_BODY}}
    }

static func from_dict(data: Dictionary) -> {{CLASS_NAME}}:
    var instance = {{CLASS_NAME}}.new()
    {{FROM_DICT_BODY}}
    return instance

func is_valid() -> bool:
    {{VALIDATION}}
    return true
```

## 模板变量说明

| 变量 | 说明 |
|------|------|
| `{{CLASS_NAME}}` | 类名 |
| `{{CLASS_DESCRIPTION}}` | 类描述 |
| `{{BASE_CLASS}}` | 基类 |
| `{{SIGNALS}}` | 信号定义 |
| `{{EXPORTS}}` | 导出变量 |
| `{{PUBLIC_METHODS}}` / `{{PRIVATE_METHODS}}` | 公共/私有方法 |

## 代码质量检查

生成后应自查：
1. 语法正确（可通过 MCP 脚本校验工具验证）
2. 类型标注完整
3. 命名符合约定
4. 类描述 + 关键方法注释齐全
5. 信号定义与使用一致
