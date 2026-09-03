---
name: player-system
description: >
  玩家控制系统。生成完整的玩家控制器：移动、跳跃、攻击、状态机。
  支持 2D 平台跳跃、俯视角 2D、第三人称 3D、第一人称 3D。
  当用户要求「玩家控制 / 角色控制 / 移动系统 / Player / 玩家移动」时激活。
---

# 玩家控制系统

生成玩家控制器，包含移动、状态机、输入处理。

## 控制器类型

| 类型 | 适用 | 基类 | 特点 |
|------|------|------|------|
| Platformer 2D | 横版/银河恶魔城/平台跳跃 | CharacterBody2D | 重力、Coyote Time、跳跃缓冲、可变跳跃高度 |
| Top-down 2D | RPG/动作冒险/射击 | CharacterBody2D | 8 方向移动、平滑旋转 |
| Third Person 3D | 动作 RPG/冒险 | CharacterBody3D | 摄像机联动方向、斜坡、阶梯 |
| First Person 3D | FPS/探索/恐怖 | CharacterBody3D | 鼠标视角、头部摇摆 |

## Platformer 2D 场景结构

```
Player (CharacterBody2D)
├── CollisionShape2D
├── Sprite2D / AnimatedSprite2D
├── AnimationPlayer
├── StateMachine
│   ├── IdleState / RunState / JumpState / FallState
│   ├── DashState (可选) / AttackState (可选)
├── Hitbox (Area2D) - 攻击判定
├── Hurtbox (Area2D) - 受伤判定
├── CoyoteTimer / JumpBufferTimer
└── Camera2D (可选)
```

## Platformer 2D 主脚本

```gdscript
class_name Player2D
extends CharacterBody2D

signal died
signal health_changed(old_value: int, new_value: int)
signal jumped
signal landed

const GRAVITY: float = 980.0

@export_group("Movement")
@export var move_speed: float = 200.0
@export var acceleration: float = 1500.0
@export var friction: float = 1200.0
@export var air_friction: float = 600.0

@export_group("Jump")
@export var jump_velocity: float = -350.0
@export var max_jumps: int = 1
@export var coyote_time: float = 0.1
@export var jump_buffer_time: float = 0.1
@export var variable_jump_multiplier: float = 0.5

@export_group("Stats")
@export var max_health: int = 100

var current_health: int:
    set(value):
        var old = current_health
        current_health = clampi(value, 0, max_health)
        health_changed.emit(old, current_health)
        if current_health <= 0:
            _die()

var is_alive: bool:
    get: return current_health > 0

var facing_direction: int = 1
var jumps_remaining: int = 0
var can_coyote_jump: bool = false
var jump_buffered: bool = false

@onready var sprite: Sprite2D = $Sprite2D
@onready var coyote_timer: Timer = $CoyoteTimer
@onready var jump_buffer_timer: Timer = $JumpBufferTimer

func _ready() -> void:
    current_health = max_health
    jumps_remaining = max_jumps
    _setup_timers()

func _physics_process(delta: float) -> void:
    if not is_alive:
        return
    if not is_on_floor():
        velocity.y += GRAVITY * delta
    var input_dir = Input.get_axis("move_left", "move_right")
    if input_dir != 0:
        facing_direction = signi(input_dir)
        sprite.flip_h = facing_direction < 0
    move_and_slide()
    if is_on_floor():
        jumps_remaining = max_jumps
        if jump_buffered:
            jump()

func _unhandled_input(event: InputEvent) -> void:
    if not is_alive:
        return
    if event.is_action_pressed("jump"):
        _handle_jump_input()
    if event.is_action_released("jump"):
        _handle_jump_release()

func apply_movement(delta: float, direction: float) -> void:
    if direction != 0:
        velocity.x = move_toward(velocity.x, direction * move_speed, acceleration * delta)
    else:
        var f = friction if is_on_floor() else air_friction
        velocity.x = move_toward(velocity.x, 0, f * delta)

func _handle_jump_input() -> void:
    if is_on_floor() or can_coyote_jump:
        jump()
    elif jumps_remaining > 0:
        jump()
    else:
        jump_buffered = true
        jump_buffer_timer.start(jump_buffer_time)

func _handle_jump_release() -> void:
    if velocity.y < 0:
        velocity.y *= variable_jump_multiplier

func jump() -> void:
    velocity.y = jump_velocity
    jumps_remaining -= 1
    jump_buffered = false
    can_coyote_jump = false
    jumped.emit()

func start_coyote_time() -> void:
    can_coyote_jump = true
    coyote_timer.start(coyote_time)

func take_damage(amount: int, knockback: Vector2 = Vector2.ZERO) -> void:
    if not is_alive:
        return
    current_health -= amount
    if knockback != Vector2.ZERO:
        velocity = knockback

func _die() -> void:
    died.emit()

func _setup_timers() -> void:
    coyote_timer.one_shot = true
    coyote_timer.timeout.connect(func(): can_coyote_jump = false)
    jump_buffer_timer.one_shot = true
    jump_buffer_timer.timeout.connect(func(): jump_buffered = false)

func get_input_direction() -> float:
    return Input.get_axis("move_left", "move_right")
```

## 通用状态机

```gdscript
# state_machine.gd
class_name StateMachine
extends Node

signal state_changed(old_state: State, new_state: State)

@export var initial_state: State

var current_state: State
var states: Dictionary = {}

func _ready() -> void:
    for child in get_children():
        if child is State:
            states[child.name.to_lower()] = child
            child.state_machine = self
            child.player = get_parent()
    if initial_state:
        current_state = initial_state
        current_state.enter()

func _physics_process(delta: float) -> void:
    if current_state:
        current_state.physics_update(delta)
        var next = current_state.get_transition()
        if next != &"":
            transition_to(next)

func _unhandled_input(event: InputEvent) -> void:
    if current_state:
        current_state.handle_input(event)

func transition_to(state_name: StringName) -> void:
    var new_state = states.get(str(state_name).to_lower())
    if new_state == null or new_state == current_state:
        return
    var old = current_state
    current_state.exit()
    current_state = new_state
    current_state.enter()
    state_changed.emit(old, new_state)
```

```gdscript
# state.gd
class_name State
extends Node

var state_machine: StateMachine
var player: CharacterBody2D

func enter() -> void: pass
func exit() -> void: pass
func update(_delta: float) -> void: pass
func physics_update(_delta: float) -> void: pass
func handle_input(_event: InputEvent) -> void: pass
func get_transition() -> StringName: return &""
```

```gdscript
# run_state.gd 示例
class_name RunState
extends State

func physics_update(delta: float) -> void:
    player.apply_movement(delta, player.get_input_direction())

func get_transition() -> StringName:
    if not player.is_on_floor():
        player.start_coyote_time()
        return &"fall"
    if player.get_input_direction() == 0:
        return &"idle"
    return &""
```

## Top-down 2D 要点

```gdscript
class_name PlayerTopdown
extends CharacterBody2D

@export var move_speed: float = 200.0
@export var acceleration: float = 2000.0
@export var friction: float = 1800.0

var look_direction: Vector2 = Vector2.RIGHT

func _physics_process(delta: float) -> void:
    var input_dir = Input.get_vector("move_left", "move_right", "move_up", "move_down")
    if input_dir != Vector2.ZERO:
        look_direction = input_dir.normalized()
        velocity = velocity.move_toward(input_dir * move_speed, acceleration * delta)
    else:
        velocity = velocity.move_toward(Vector2.ZERO, friction * delta)
    move_and_slide()
```

## Third Person 3D 要点

移动方向相对摄像机基座旋转：

```gdscript
var camera_basis = camera_pivot.global_transform.basis
var direction = (camera_basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
direction.y = 0
```

## 输入映射配置

生成玩家系统时，在 `project.godot` 添加 `[input]` 段定义动作：

| 动作 | 默认键 |
|------|--------|
| move_left / move_right | A / D |
| move_up / move_down | W / S |
| jump | Space |
| dash | Shift |
| attack | 鼠标左键 |

## 使用示例

```
创建一个 2D 平台跳跃玩家控制器：支持移动、跳跃、二段跳、冲刺，包含完整状态机。
```
