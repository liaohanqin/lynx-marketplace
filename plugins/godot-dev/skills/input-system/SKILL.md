---
name: input-system
description: >
  输入系统。管理游戏输入映射，支持键盘/手柄/触屏多种输入方式。
  当用户要求「输入映射 / 按键 / 手柄 / 键盘 / 操作方式 / 快捷键」时激活。
---

# 输入系统

管理游戏输入映射。

## 输入映射配置

Godot 4 通过 `project.godot` 的 `[input]` 段定义输入动作（Input Map）。
也可在编辑器 Project Settings → Input Map 里配置。

### 常用动作映射

```ini
[input]

move_left={
"deadzone": 0.2,
"events": [Object(InputEventKey,"keycode":65)]
}
move_right={
"deadzone": 0.2,
"events": [Object(InputEventKey,"keycode":68)]
}
move_up={
"deadzone": 0.2,
"events": [Object(InputEventKey,"keycode":87)]
}
move_down={
"deadzone": 0.2,
"events": [Object(InputEventKey,"keycode":83)]
}
jump={
"deadzone": 0.5,
"events": [Object(InputEventKey,"keycode":32)]
}
dash={
"deadzone": 0.5,
"events": [Object(InputEventKey,"keycode":4194325)]
}
attack={
"deadzone": 0.5,
"events": [Object(InputEventMouseButton,"button_index":1)]
}
interact={
"deadzone": 0.5,
"events": [Object(InputEventKey,"keycode":69)]
}
```

## 代码读取输入

```gdscript
# 轴输入（返回 -1..1，支持手柄摇杆）
var axis = Input.get_axis("move_left", "move_right")

# 向量输入（2D/3D 方向）
var vec2 = Input.get_vector("move_left", "move_right", "move_up", "move_down")
var vec3 = Input.get_vector("move_left", "move_right", "move_up", "move_down")

# 按下瞬间（仅当帧触发）
if Input.is_action_just_pressed("jump"):
    jump()

# 持续按住
if Input.is_action_pressed("sprint"):
    speed = sprint_speed

# 松开瞬间
if Input.is_action_just_released("jump"):
    _handle_jump_release()
```

## 输入事件处理

在节点里通过 `_unhandled_input` 或 `_input` 处理事件：

```gdscript
func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("jump"):
        _handle_jump_input()
    elif event.is_action_pressed("attack"):
        attack()
```

- `_input`：优先处理，会拦截输入
- `_unhandled_input`：在 UI 未消费输入后才收到，适合游戏逻辑

## 最佳实践

1. 用动作名（action）而非硬编码键码，便于改键和手柄适配。
2. 动作名用 snake_case，语义化（`move_left` 而非 `key_a`）。
3. 支持手柄时，同一动作绑定键盘 + 手柄两个事件。
4. UI 输入用 Godot 内置的 `ui_*` 动作（`ui_accept`/`ui_cancel` 等），不要自定义。
