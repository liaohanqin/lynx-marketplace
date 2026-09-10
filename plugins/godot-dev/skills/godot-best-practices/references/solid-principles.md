# SOLID 五原则在 Godot 的应用

> 本文档对应《Godot 4 Best Practices》第 1 章，提炼 SOLID 五原则在 Godot 节点/场景体系下的应用方法。

SOLID 是面向对象设计的五个原则，目的是让代码**可理解、灵活、可维护、可扩展、可测试**。它们是「设计原则」而非「铁律」——小原型、Game Jam、早期实验时优先做出可玩版本，不要为了架构完美而过度设计。原则应当指导决策，而非支配决策。

在 Godot 里，脚本（script = 逻辑/继承/契约）与场景（scene = 结构/组合/封装）一起充当传统 OOP 中「类」的角色。所以可以把 OOP 原则直接应用到节点和场景树。

---

## S — 单一职责原则（SRP）

### 核心原则

一个脚本只做一件事，只有一个「需要修改的理由」。

### 适用场景

- 脚本越来越大、职责混杂（输入、移动、血量、UI、音频挤在一起）
- 团队协作、版本控制中频繁冲突的巨型脚本
- 需要复用某个行为到其它对象时

### 反模式

一个 Player 脚本同时管移动、血量、UI 更新、音效：

```gdscript
# Player.gd (违反 SRP)
extends CharacterBody2D
@onready var health_label = $UI/HealthLabel
@onready var audio_player = $AudioStreamPlayer2D

func _physics_process(delta):
    var input = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
    velocity = input * 300.0
    move_and_slide()

func take_damage(amount):
    health -= amount
    health_label.text = "HP: " + str(health)   # 耦合 UI
    audio_player.play()                          # 耦合音频
```

问题：移动 `HealthLabel` 就崩溃；想复用移动逻辑给 NPC 却无法剥离 UI/音频。

### 正确做法

用信号解耦，Player 只发事件、不关心谁监听：

```gdscript
# Player.gd (重构后)
extends CharacterBody2D
signal health_changed(new_value)
signal player_damaged
var health = 100

func take_damage(amount):
    health -= amount
    health_changed.emit(health)
    player_damaged.emit()
```

UI 脚本监听 `health_changed`，音频管理器监听 `player_damaged`，各自独立。

### 在 Godot 里落地

- **用子节点**：不要只在 Player 里放 `AudioStreamPlayer`，而是给它挂专门脚本（如 `AudioManager.gd`），Player 只调 `play_footstep()`。
- **用组件**：血量逻辑拆成 `HealthComponent` 节点，挂到 Player 上，把职责推出根脚本。

### 权衡与陷阱

SRP 也适用于**函数**——`_process`/`_physics_process` 应作为「高级调度器」，把逐帧逻辑委托给 `handle_input()`、`apply_gravity()`、`move_character()` 等单一职责函数，而不是塞满几十行判断。过早拆分也会增加跳转成本，小型原型不必强求。

---

## O — 开闭原则（OCP）

### 核心原则

能新增功能而**不修改**既有代码——对扩展开放，对修改封闭。

### 适用场景

- 敌人/武器/道具种类会持续增长
- 用大量 `if/elif` 或 `match` 按名字分派行为的场景

### 反模式

在 Player 里按敌人名字硬编码分派：

```gdscript
# 反模式：每个新敌人都要改 Player
func _on_body_entered(body: Node2D) -> void:
    if body.is_in_group("enemies"):
        if body.name == "Archer":
            body.shoot_arrow(self)
        elif body.name == "Knight":
            body.slash(self)
        elif body.name == "Boss":
            body.special_attack(self)
```

### 正确做法

定义基类 + 子类继承覆盖：

```gdscript
# Enemy 基类
class_name Enemy extends CharacterBody2D
@export var damage: int = 10
func _ready() -> void:
    add_to_group("enemies")

# Archer 子类
class_name Archer extends Enemy
func attack(target: Node) -> void:
    if target and target.has_method("take_damage"):
        target.take_damage(damage)

# Player 只认抽象契约
func _on_enemy_detector_body_entered(body: Node2D) -> void:
    if body.is_in_group("enemies") and body.has_method("attack"):
        body.attack(self)
```

### 在 Godot 里落地

- **继承**：用 `extends` 创造变体（`Goblin.gd` 继承 `Enemy.gd`）而不改基类。
- **Resource**：OCP 的「超能力」。定义 `WeaponStats extends Resource`，用导出变量建几百个 `.tres`（`Dagger.tres`、`Axe.tres`），只改 Inspector 数字即可扩展内容，完全不动源码。

### 权衡与陷阱

`has_method("attack")` 是**鸭子类型**（灵活，但牺牲类型安全）；`if body is Enemy` 是**显式类型**（安全 + 自动补全，但牺牲灵活性——`SpikeTrap` 有 `attack()` 却非 `Enemy` 会被拒绝）。项目规模大时更推荐显式类型，小项目可用鸭子类型。

---

## L — 里氏替换原则（LSP）

### 核心原则

子类必须能在任何父类被期望的地方无缝替换，不破坏程序。

### 适用场景

任何继承关系的设计；尤其 GDScript 动态类型下，LSP 是防运行时崩溃的安全网。

### 反模式

子类改变父类方法的签名/返回值：

```gdscript
# 父类
class_name Enemy extends CharacterBody2D
var health: int = 50
func get_health() -> int:
    return health

# 反模式：Goblin 覆盖成 String，破坏契约
extends Enemy
func get_health():
    return "My health"   # 返回类型变了 → 运行时崩溃
```

### 正确做法

保持契约不变，需要新信息时**新增方法**而非改签名：

```gdscript
extends Enemy
var max_health: int = 100
func get_health() -> int:      # 契约不变
    return health
func get_max_health() -> int:  # 新增能力
    return max_health
```

调用方可选择性检查新能力：`if body.has_method("get_max_health")`。

### 权衡与陷阱

GDScript 默认动态类型（除非用严格静态类型），编辑器不会警告「子类删了 `take_damage()` 或改了参数」——游戏会在运行时直接崩。规则：继承父类后，子类必须能处理父类能处理的所有方法和信号调用。

---

## I — 接口隔离原则（ISP）

### 核心原则

不要强迫脚本携带它不需要的能力；接口小而专一。

### 适用场景

- 巨型 `Entity` 基类塞满 `fly()`/`swim()`/`cast_magic()` 而大多数子类用不上
- 基类 API 膨胀，子类被迫继承无用/死代码

### 反模式

在 `Enemy` 基类里放所有攻击方式，Archer 继承后被迫带上投矛、喷火等无关方法。

### 正确做法

让基类最小化，只含共享状态（属性）和真正通用的行为（方法）：

```gdscript
# Enemy 基类只保留通用逻辑
func take_damage(amount: int) -> void:
    health -= amount
    if health <= 0:
        _die()

func _die() -> void:
    queue_free()
```

具体攻击逻辑放子类（如 Goblin 的 `_ignite_target` 灼烧），避免基类「方法污染」。

### 在 Godot 里落地

- **聚焦的信号**：别用 `player_updated(data_dict)` 一个大字典信号，改用 `health_depleted`、`ammo_changed` 等细分信号，让监听者只关心自己需要的数据。
- **节点组合**：能飞的敌人挂 `FlyComponent`，不能飞的就不挂——不给对象塞空方法。

### 权衡与陷阱

Godot 没有 C#/Java 那样的 `interface` 关键字，ISP 通过「信号 + 组件」实现。基类太大是 OCP 的隐患（加新攻击类型要改基类，改动会波及所有子类）。

---

## D — 依赖倒置原则（DIP）

### 核心原则

高层逻辑不依赖低层细节，两者都依赖抽象（信号/接口）。

### 适用场景

- 脚本里大量 `get_node("../xxx")` 硬编码路径
- 敌人直接改 Player 内部变量、直接更新 HUD 的跨层耦合

### 反模式

```gdscript
# Archer.gd (反模式)
func attack():
    var player = get_node("../Player")   # 硬编码路径，脆弱
    player.health -= 10                   # 直接改内部变量
    var hud = get_node("../HUD")          # 敌人耦合 UI
    hud.update_health(player.health)
```

### 正确做法

Player 发信号，UI 监听信号，敌人只调 `take_damage()`：

```gdscript
# Player.gd 依赖抽象（信号）
func take_damage(amount):
    Events.player_damaged.emit(amount)
```

### 用 Autoload 实现依赖倒置：Signal Bus

局部依赖用 `@export` 注入；全局依赖用 Autoload 当「信号总线」抽象：

```gdscript
# Events.gd (Autoload) — 定义抽象
extends Node
signal player_damaged(amount)
signal game_over

# Player.gd — 只依赖抽象
func take_damage(amount):
    Events.player_damaged.emit(amount)

# HealthBar.gd — 低层细节也依赖抽象
func _ready():
    Events.player_damaged.connect(_on_player_damaged)
```

这样 Player 不知道 UI 存在，可完全替换 UI/音频系统而不动 Player 逻辑。

### 在 Godot 里落地

- **`@export var target: Node2D`**：通过 Inspector 注入依赖，脚本不关心节点在树里的位置。
- **信号**：子节点发信号，父节点监听——依赖方向反转（父依赖子，而非子依赖父的具体实现）。
- **`@export` + `_get_configuration_warnings()`**：用 `@tool` + 警告函数提醒「忘记拖节点进 Inspector 槽位」的错误，在编辑器里就暴露问题。

### 权衡与陷阱

`@export` 注入强类型（如 `AudioComponent` 而非 `Node`）能获得自动补全和类型安全，但牺牲灵活性（只接受继承自 `AudioComponent` 的节点）。用 `_get_configuration_warnings()` 缓解「忘记赋值」的风险。

---

## 综合应用：可扩展的交互系统

把 OCP + ISP 组合，构建一个「加了新交互物也不用改 Player」的系统：

```gdscript
# Interactable.gd — 定义契约
class_name Interactable extends Area2D
func interact(user: Node):
    pass

# Chest.gd — 具体实现
extends Interactable
func interact(user: Node):
    print("You found gold!")
    queue_free()

# Player.gd — 对修改封闭
@export var interaction_area: Area2D
func _unhandled_input(event):
    if event.is_action_pressed("interact"):
        for area in interaction_area.get_overlapping_areas():
            if area is Interactable:
                area.interact(self)
                return
```

以后加门、NPC、拉杆、存档点，都不需要再打开 Player 脚本。

---

## 落地：feature-based 目录结构

SOLID 也适用于项目结构。新手常按**类型**分文件夹（`Scripts/`、`Scenes/`、`Sprites/`），处理「Player」要跳三个目录。可扩展的替代方案是**按 feature 分**：

```
res://Player/          → Player.gd, Player.tscn, PlayerIcon.png
res://Enemies/Goblin/  → Goblin.gd, Goblin.tscn, GoblinSkins.png
res://UI/HUD/          → HUD.gd, HUD.tscn, HealthBar.png
```

好处：系统自包含（封装），复用 Player 时拖整个文件夹即可带走全部依赖。

---

## 原则速查表

| 原则 | 一句话 | 主要落地手段 |
|------|--------|-------------|
| SRP | 一个脚本一个职责 | 子节点、组件、信号 |
| OCP | 扩展不改旧代码 | 继承、Resource |
| LSP | 子类可替换父类 | 保持方法签名契约 |
| ISP | 接口小而专一 | 聚焦信号、组件组合 |
| DIP | 依赖抽象不依赖细节 | `@export` 注入、Signal Bus |

> **提醒**：这些原则服务于「可玩的游戏」，不是反过来。玩家不关心代码怎么写，只关心玩起来怎么样。原则让开发者的工作更轻松时才使用它。
