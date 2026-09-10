# Godot 设计模式参考（第 5–10 章）

> 本文档提炼自《Godot 4 Best Practices》**第 5 章至第 10 章**：
> Autoload/Singleton、Event-Driven、State/Strategy、Component-Based、Factory/Builder、Command/Service。
> 每个模式按「核心原则 → 适用场景 → 反模式 → 正确做法 → 权衡与陷阱」组织。

---

## 1. Autoload 与 Singleton 模式

### 核心原则
Autoload 是 Godot 对 **Singleton Pattern** 的原生实现：引擎在场景树最顶层（`/root` 的直接子节点）自动实例化一次，因此它**随游戏启动而存在、跨场景切换不被销毁、全局可按名字访问**。

### 适用场景
只用于**持续运行的后台系统（Service）**，而非数据容器：

- `AudioManager`：音乐不因换关而中断。
- `SceneLoader`：需要用 `ResourceLoader` 做淡入淡出/加载进度时，它是唯一存活到两次场景之间的对象。
- `NetworkManager`：跨大厅/关卡保持 socket 连接。
- `EventBus`：只放 signal 的通信插线板。
- 应用级配置（分辨率、音量）。

```gdscript
# AudioManager.gd (Autoload)
AudioManager.crossfade_music("res://audio/boss_theme.ogg")  # 任意脚本可调用
```

### 反模式
**把所有东西塞进一个 `Global.gd`（God Object）。**

```gdscript
# Global.gd — 反面教材
extends Node
var player_hp
var inventory_list
var is_game_over
func save_game() -> void: pass
func play_sound() -> void: pass
```

为什么错：它同时充当数据库、音频引擎、状态机、IO 系统，违反单一职责；导致
- **紧耦合**：底层对象被硬编码依赖某个具名全局（`get_node()` 或全局名都失踪即崩溃）。
- **不可移植**：`Coin` 无法丢进没有 `GameManager` 的测试场景或别的项目。
- **竞态条件 / 内存膨胀 / 重构噩梦**：任何脚本都能随时改同一个值；Autoload 常驻内存永不释放；改名要改几十个文件。

```gdscript
# 反模式：底层对象直接指挥全局
class_name Coin extends Area2D
func _on_body_entered(body):
    GameManager.add_score(10)  # Coin 永久耦合 GameManager
    queue_free()
```

### 正确做法
**原则：Autoload 管系统（system），不管数据（state）。**

- 不要 `PlayerStats` 作为 Autoload（玩家数据属于 Player 节点或 Resource）。
- 要 `AudioService` 作为 Autoload（播放声音是全游戏通用的服务能力）。

**用信号解耦（推荐）：**让底层对象只广播，由「语境拥有者」（Level/Spawner）负责接线。

```gdscript
# Coin.gd — 只广播，不关心谁记分
class_name Coin extends Area2D
signal coin_collected(amount: int)

func _on_body_entered(body: Node2D) -> void:
    coin_collected.emit(10)
    queue_free()

# level.gd — 中间人负责接线
func _ready() -> void:
    $Coin.coin_collected.connect(GameManager.add_score)
```

**用 Setter 注入服务（需要持续调用服务时）：**定义接口，变量可替换，便于隔离测试。

```gdscript
# AudioServiceInterface.gd (Godot 4.5+ @abstract)
@abstract
class_name AudioServiceInterface extends Node

@abstract
func play_sfx(sound_name: String) -> void:
    pass

# Player.gd — 变量而非硬编码全局
class_name Player extends CharacterBody2D
var audio_service: AudioServiceInterface

func _ready() -> void:
    audio_service = AudioManager  # 默认注入全局，但可替换

func jump() -> void:
    audio_service.play_sfx("jump")

# 测试时注入假实现，无需加载真实音频
class_name AudioDummy extends AudioServiceInterface
func play_sfx(_sound_name: String) -> void:
    pass
```

### 权衡与陷阱
不要用 Autoload 的场景：
- **玩家/关卡状态**：死亡回主菜单后数据残留，得手动重置；一旦要本地多人，全局 `PlayerManager` 架构直接崩塌。改用 Resource 或本地场景树传递。
- **重型视觉场景**（暂停菜单、粒子系统）：Autoload 常驻内存，应放回需要的关卡内。

**Singleton 的替代方案对比：**

| 方案 | 最佳用途 | 优点 | 缺点 |
|---|---|---|---|
| Autoload (Singleton) | 持久后台系统（音频、总线、网络） | 跨场景存活；无需复杂节点路径 | 易滥用成 God Object；给本地逻辑引入紧耦合 |
| Custom Resource | 静态数据、道具数值、配置 | 与场景树解耦；轻量；天然可复用 | 不能跑 `_process` 等持续逻辑；动态持久化需手动存读 |
| Groups | 批量操作、语义打标签（`Enemies`/`Destructibles`） | 松耦合；绕过层级直接命令多个节点 | 依赖 magic string，无自动补全；方法名拼错会静默失败 |
| Static Functions | 无状态工具/数学计算 | 零节点开销；全局可调 | 不能持有活跃状态；不能自动访问场景树或生命周期函数 |

```gdscript
# 无状态工具：不需要 Autoload 节点
class_name Utils
static func calculate_damage(a: int, b: int) -> int:
    return a - b
```

> 注：Group 命令是「发出去就不管」的——没人监听时静默通过；而 `SoundManager.play()` 这类 Singleton 调用在管理器被删时会直接崩溃。

---

## 2. 事件驱动架构（Event-Driven / Event Bus）

### 核心原则
**扩展黄金法则：Call Down, Signal Up, Event Out。**

- **Call Down（父→子）**：父节点对子节点有完全权威，可直接调用其函数。
- **Signal Up（子→父）**：子节点不应知道父节点是谁，只负责**上报发生的事实**，不决定别人如何反应。
- **Event Out（跨系统）**：面向完全无关的系统（UI、成就、音频）时，向全局 **Event Bus** 广播事件，而不是在树里找它们。

### 适用场景
- 跨越系统边界的一次性事件（敌人死亡、得分变化、子弹发射）。
- 两个毫不相关的场景树分支需要通信（PlayerShip 与 HealthBar 分属不同子树）。
- 需要持久、可被多方订阅的**状态**时，用 Observable Resource（下文）。

### 反模式
**直接引用 / 轮询（polling）**：对象必须知道对方的精确路径和类型。

```gdscript
# 反面教材
func take_damage(amount: int) -> void:
    health -= amount
    var health_bar = get_node("../CanvasLayer/HealthBar")  # 移动/重命名即崩
    health_bar.update_health(health)
```

为什么错：`HealthBar` 一移动或改名 Game 就崩；单独测试 `Player` 场景（无 UI）也崩；对象被 `queue_free()` 后引用变 null。整个项目变成硬依赖的网。

### 正确做法

**基础解耦：SIGNAL UP（只广播，谁听由对方决定）**

```gdscript
# Player.gd
signal health_changed(new_value: int)

func take_damage(amount: int) -> void:
    health -= amount
    health_changed.emit(health)  # 不关心谁听
```

**运行时动态连接（对象是运行期生成的，编辑器里没得点）：**

```gdscript
func spawn_enemy() -> void:
    var enemy = enemy_scene.instantiate()
    add_child(enemy)
    enemy.died.connect(_on_enemy_died)  # 注意：传函数引用，不带括号
```

**Event Bus（发布/订阅）：**一个只定义 signal、不含逻辑的 Autoload。

```gdscript
# EventBus.gd (Autoload)
@warning_ignore("unused_signal")
extends Node

signal score_changed(new_amount: int)
signal player_lives_changed(current_lives: int)
signal weapon_changed(weapon_name: String, ammo: int)

# 发射方：广播后立即退场
func die() -> void:
    EventBus.score_changed.emit(score_value)
    queue_free()

# 订阅方：只认识 Event Bus
func _ready() -> void:
    EventBus.score_changed.connect(update_score)
```

要点：`extends Node`（保持最小内存占用）；参数显式类型化（广播类型错误会立即报错，而非静默 bug）；`unused_signal` 警告可安全忽略。

**命名空间（信号太多时按域分组）：**

```gdscript
# EventBus.gd
extends Node

class PlayerEvents:
    signal health_changed(new_health: int)
    signal died

class WorldEvents:
    signal asteroid_destroyed(size: int)

var Player = PlayerEvents.new()   # 必须实例化，否则无法 emit
var World = WorldEvents.new()

# 使用：EventBus.Player.health_changed.emit(health)
```

**Event Object（payload 会频繁变化时，防止改签名波及所有订阅者）：**

```gdscript
class_name EnemyDeathEvent extends RefCounted
var points: int
var position: Vector2
var enemy_type: String

# 发射
var e = EnemyDeathEvent.new()
e.points = 100
EventBus.enemy_destroyed.emit(e)

# 订阅：签名永远只有一个参数，加字段不破坏旧订阅者
func _on_enemy_destroyed(event: EnemyDeathEvent) -> void:
    score += event.points
```

**Signals vs Notifications 抉择：**

| 维度 | Signals | Notifications |
|---|---|---|
| 方向 | 一个对象说话，多个监听 | 引擎告知某个对象发生了事 |
| 定制 | 自定义名字与参数 | 只能用引擎整数常量 |
| 性能 | 略慢（有解析开销） | 极快（C++ 层） |
| 最佳用途 | 玩法逻辑、UI 更新、任务触发 | 内存管理、OS 交互、对象清理 |

```gdscript
# Notifications 示例：访问无专用 helper 的生命周期事件
func _notification(what: int) -> void:
    match what:
        NOTIFICATION_WM_FOCUS_OUT:      # Alt-Tab 失去焦点，自动暂停
            get_tree().paused = true
        NOTIFICATION_WM_CLOSE_REQUEST:  # 关闭窗口前存档
            save_game()
```

**Observable Resource（状态用「名词」，事件用「动词」）：**

```gdscript
# player_stats.gd
class_name PlayerStats extends Resource

signal shield_capacity_changed(new_capacity: int)

@export var max_shield: int = 50:
    set(value):
        max_shield = value
        shield_capacity_changed.emit(max_shield)
```

把 `PlayerStats.tres` 同时给 Player、HUD、SaveManager 时，它们指向内存中同一对象。升级站只写 `stats.max_shield = 100`，UI 自动同步，无需中央管理器。Resource 是引用计数的（无人引用会自动释放），而 Autoload 从头到尾常驻。

**Push/Pull 架构（解决启动期竞态）：**

```gdscript
func _ready() -> void:
    # Push：订阅未来的变化
    EventBus.score_changed.connect(update_score)

    # Pull：主动拉取当前状态（HUD 可能晚于 Player 加载）
    update_score(EventBus.current_score)
```

### 权衡与陷阱
Event-Driven 的三大风险与对策：

1. **级联事件（Spaghetti Logic）**：A 触发 B 再触发 C，无法线性阅读，可能死循环。
   → 强制 **One-Hop Rule**：一个事件只触发**最终反应**（更新 UI、播音、改一个状态），不再发新事件。若必须严格顺序，用专门 Manager 监听首事件后用直接函数调用执行后续步骤。
2. **系统顺序（race condition）**：总线同时广播，无法保证谁先处理。
   → **绝不用 Event Bus 做有顺序依赖的逻辑**。若 A 依赖 B 先算完，用 Call Down 或显式委托。Event Bus 只用于彼此独立、顺序无关的并行反应。
   → 另：节点 `_ready` 由底向上执行，谁先「打开收音机」不可保证；无状态总线不保存历史，启动前发出的事件会永久丢失。用 Observable Resource + Pull 兜底。
3. **可追溯性（Bad Actor）**：任何脚本都能发任何事件（如子弹误发 `level_completed`），且无回溯路径。
   → 重大全局事件要求带来源：`signal level_completed(source: Node, reason: String)`，便于定位流氓脚本。

其他陷阱：`await` 可以避免把时序逻辑拆到多个回调（`await animation_player.animation_finished`），但滥用会造成隐式控制流。

---

## 3. State 模式（有限状态机）

### 核心原则
State 模式是 FSM 的面向对象实现：**把对象抽象的状态变成可互换的物理对象（每个状态一个脚本/Node），任意时刻只处于一个状态，用明确的 transition 规则切换。** 用 **委托** 代替庞大的 `if/elif`。

### 适用场景
- 对象有明显的阶段/心情切换（Patrol → Chase → Attack；多阶段 Boss 战）。
- 单体脚本出现 **code smell**：Boolean 泛滥（`is_jumping/is_attacking/is_crouching`）、`match` 超 50 行、改一处坏另一处。

### 反模式
**用 enum + match 手写劣质状态机：**

```gdscript
enum MovementType { NORMAL, BOOSTING, DISABLED }
var current_movement = MovementType.NORMAL

func _physics_process(delta):
    match current_movement:
        MovementType.NORMAL:
            speed = 300; process_normal_input()
        MovementType.BOOSTING:
            speed = 600; process_boost_input(); drain_energy()
        MovementType.DISABLED:
            speed = 0; play_sparks_effect()
```

为什么错：加一个 `EMP_STUNNED` 要改 enum、加 case、往 Player 里塞新变量；`player.gd` 会膨胀到上千行；每个 flag 都让 if 复杂度翻倍；改一处功能可能引发连锁破坏（shotgun surgery）。

### 正确做法
**Base State（契约）+ StateMachine（管理器）+ 各状态脚本。**

```gdscript
# state.gd — 所有状态的模板/契约
class_name State extends Node

@export var state_id: String = ""   # 用 id 而非脆弱的节点名
signal transition_requested(state: State, new_state_id: String)

func enter() -> void: pass
func exit() -> void: pass
func update(_delta: float) -> void: pass
func physics_update(_delta: float) -> void: pass
```

```gdscript
# state_machine.gd — 只做路由，不写玩法逻辑
class_name StateMachine extends Node

@export var initial_state: State
var current_state: State
var states: Dictionary[String, State] = {}

func _ready() -> void:
    for child in get_children():
        if not child is State:
            continue                     # guard clause
        var key: String = child.name
        if child.state_id != "":
            key = child.state_id
        states[key.to_lower()] = child
        child.transition_requested.connect(on_state_transition_requested)

    if initial_state:
        initial_state.enter()
        current_state = initial_state

func _process(delta: float) -> void:
    if current_state:
        current_state.update(delta)

func _physics_process(delta: float) -> void:
    if current_state:
        current_state.physics_update(delta)

func on_state_transition_requested(state: State, new_state_id: String) -> void:
    if state != current_state:
        return                           # 忽略旧状态的延迟信号（ghost transition）
    var new_state: State = states.get(new_state_id.to_lower())
    if not new_state:
        push_warning("State does not exist: ", new_state_id)
        return
    current_state.exit()
    new_state.enter()
    current_state = new_state
```

```gdscript
# chase.gd — 单一职责：只关心「追」和「何时交接」
class_name Chase extends State

@export var actor: CharacterBody2D      # 被控实体（State 自身没有物理位置）
@export var speed: float = 150.0
@export var attack_range: float = 200.0
var target: Node2D

func enter() -> void:
    target = get_tree().get_first_node_in_group("Player")

func physics_update(delta: float) -> void:
    # 阶段 1：guard clauses（先决策，再执行）
    if not target:
        transition_requested.emit(self, "Patrol")
        return
    if actor.global_position.distance_to(target.global_position) <= attack_range:
        transition_requested.emit(self, "Attack")
        return

    # 阶段 2：转向与推进
    var direction = (target.global_position - actor.global_position).normalized()
    var target_rotation = direction.angle() + PI / 2.0   # 精灵默认朝上
    actor.rotation = lerp_angle(actor.rotation, target_rotation, 3.0 * delta)
    var forward = Vector2.UP.rotated(actor.rotation)
    actor.velocity = forward * speed
    actor.move_and_slide()
```

用 Node 建 FSM 的理由：场景树可直接看到敌人有哪些行为（自文档化）；状态天然接入 `_process/_physics_process`；Remote Scene Tree 可实时看到当前激活状态。这与「用代码写逻辑、用 Node 表达结构」并不矛盾——FSM 正是实体大脑的**结构**。

### 权衡与陷阱
- **过度设计**：只会开关一次的门不需要 `open_state.gd` + `closed_state.gd`，一个 `is_open` 布尔足够。
- **文件碎片化**：用几十个小文件替换一个千行大文件，若不整理目录，找文件反而更慢。
- **性能开销**：Node 开销虽小但不为零。5000 块碎片每个都挂 StateMachine 会拖垮性能——只给玩家、Boss、复杂 AI 用。

---

## 4. Strategy 模式

### 核心原则
Strategy 模式把「一个对象**如何**完成某项任务」的算法族封装成可互换对象，运行时可替换。在 Godot 中最优实现是 **Custom Resource**（纯数据对象，不在场景树中，几乎不占内存，可存为 `.tres` 并热插拔）。

### 适用场景
- 对象做**同一件事但算法不同**：多种武器（Laser / SpreadShot / Homing）、状态效果（中毒/眩晕/燃烧）、可交互物（门/宝箱/开关）。
- Boss/角色有大量行为变体，但**不由自己管理状态切换**（由父级调用）。

### State vs Strategy 抉择
- **State Pattern**：对象经历不同**阶段/心情**，状态通常互斥，对象**自己**依据内部规则频繁转换。→ Patrol / Chase / Attack。
- **Strategy Pattern**：对象执行**固定任务但算法可变**，策略**很少自己切换**，等待被父级调用。→ 按 E 触发时武器/交互方式的差异。

### 反模式
- 在 `player_ship.gd` 里用大段 `if/match` 处理各种开火方式。
- 用「场景数组 + 字符串索引」硬编码武器列表。
- 把开火数学内联，导致加武器要动 Player 脚本（shotgun surgery）。

### 正确做法
**抽象基类（契约，抛错防误用）+ 具体策略 Resource：**

```gdscript
# weapon_strategy.gd — 抽象基类/接口
class_name WeaponStrategy extends Resource

@export var fire_rate: float = 0.5
@export var energy_cost: int = 10

func fire(spawn_location: Vector2, direction: Vector2, parent_container: Node) -> void:
    push_error("Abstract method fire() must be overridden!")
```

```gdscript
# laser_strategy.gd
class_name LaserStrategy extends WeaponStrategy
@export var laser_scene: PackedScene

func fire(spawn_location: Vector2, direction: Vector2, parent_container: Node) -> void:
    var laser: Node2D = laser_scene.instantiate()
    laser.global_position = spawn_location
    laser.rotation = direction.angle() + PI / 2.0
    if parent_container:
        parent_container.add_child(laser)
    else:
        push_warning("LaserStrategy fired without a valid parent_container!")
```

```gdscript
# spread_shot_strategy.gd — 同接口的不同算法
class_name SpreadShotStrategy extends WeaponStrategy
@export var laser_scene: PackedScene
@export var spread_angle: float = 15.0

func fire(spawn_location: Vector2, direction: Vector2, parent_container: Node) -> void:
    for angle in [-spread_angle, 0, spread_angle]:
        var laser = laser_scene.instantiate()
        laser.global_position = spawn_location
        laser.rotation = direction.rotated(deg_to_rad(angle)).angle() + PI / 2.0
        if parent_container:
            parent_container.add_child(laser)
```

**注入策略（@export 槽位 + 纯委托）：**

```gdscript
class_name Blaster extends Node2D

@export var basic_weapon: WeaponStrategy
@export var upgraded_weapon: WeaponStrategy
@onready var muzzle: Marker2D = $Muzzle
@onready var cooldown_timer: Timer = $CooldownTimer

var current_strategy: WeaponStrategy
var special_ammo: int = 0

func _ready() -> void:
    current_strategy = basic_weapon

func fire() -> void:
    if not cooldown_timer.is_stopped():
        return
    if not current_strategy:
        push_error("Blaster has no strategy assigned!")
        return
    # 委托：Blaster 不再计算子弹数学
    current_strategy.fire(
        muzzle.global_position,
        Vector2.UP.rotated(global_rotation),
        get_tree().current_scene      # 传入安全的 parent_container
    )
    cooldown_timer.start(current_strategy.fire_rate)

func upgrade_weapon() -> void:
    current_strategy = upgraded_weapon
    special_ammo = 5

func downgrade_weapon() -> void:
    current_strategy = basic_weapon
```

两个必须传 `parent_container` 的架构原因：
- **相对运动问题**：若直接 `add_child(laser)` 挂在飞船下，子弹会跟随飞船移动。弹丸应放进场景树顶部的**中立容器**。
- **Resource 隔离问题**：Resource 不是 Node，没有 `add_child()` / `get_tree()`，必须由调用方（Blaster）传入活的容器作桥梁。

### 权衡与陷阱
- **紧耦合反向风险**：`@export` 槽位和 `.tres` 让策划可拖拽配置，但接口变化会影响所有策略。
- **过度颗粒化**：把简单行为拆成策略反而增加文件数。只在「同一任务、多算法、需要热插拔」时使用。
- **资源泄漏意识**：Resource 是引用计数的，未被引用会自动释放——这通常优于 Singleton 常驻。

---

## 5. 组件系统（Entity-Component / Composition）

### 核心原则
**组合优于继承。** 实体只是一个空容器（`Node2D`/`CharacterBody2D`），能力由挂载的**单一职责、独立、可复用**的 component 提供。把「对象**是什么**」的问题换成「对象**能做什么**」。

### 适用场景
- 存在大量**共享重叠行为**的多面实体（玩家、敌机、可破坏陨石、木箱、炮塔）。
- 环境物体高度可交互。
- 你发现自己开始**复制粘贴**同一段逻辑到第二个/第三个脚本（DRY 触发点）。

### 反模式
**深层继承陷阱：**

```
BaseEntity → MovingEnemy → ShootingEnemy → ...
```

为什么错：
- **Turret 问题**：炮塔要开火但不能飞，无法继承 `ShootingEnemy`（会带上飞行逻辑），只能另开分支并复制开火代码。
- **Drone 问题**：会飞会治疗但无武器的支援机也只能复制代码。
- 最终二选一：大量重复代码，或一个塞满所有特性、靠 Boolean flag 控制的 god class。

同时要避免另一个极端：**为「以后可能用到」预先设计通用组件架构**（违反 YAGNI）。只有一个敌人时就写 `var health` 更干净。

### 正确做法
**纯组件（Pure Component）= 自包含、单一职责、零外部依赖。**

```gdscript
# health_component.gd — 不知道挂载者是谁
class_name HealthComponent extends Node

signal died
signal health_changed(new_health: float, max_health: float)

@export var max_health: float = 100.0
var current_health: float

func _ready() -> void:
    current_health = max_health

func take_damage(amount: float) -> void:
    current_health -= amount
    health_changed.emit(current_health, max_health)
    if current_health <= 0:
        died.emit()
```

```gdscript
# hitbox_component.gd — 只报警，不算账
class_name HitboxComponent extends Area2D

signal hit_received(damage_amount: float)

func damage(amount: float) -> void:
    hit_received.emit(amount)   # 不知道 HealthComponent 是否存在
```

**母板方法（Motherboard / Controller）：**父实体几乎不含逻辑，只用 `_ready()` 接线。

```gdscript
# stun_cruiser.gd — 中枢交换机
class_name StunCruiser extends CharacterBody2D

@onready var hitbox: HitboxComponent = $HitboxComponent
@onready var shield: ShieldComponent = $ShieldComponent
@onready var health: HealthComponent = $HealthComponent
@onready var stun: StunComponent = $StunComponent
@onready var flash: FlashComponent = $FlashComponent

func _ready() -> void:
    hitbox.hit_received.connect(_route_incoming_damage)
    shield.shield_broken.connect(stun.trigger_stun)
    shield.shield_broken.connect(flash.trigger_flash)

func _route_incoming_damage(amount: float) -> void:
    if shield.current_health > 0:
        shield.take_damage(amount)
    else:
        health.take_damage(amount)
```

组件保持「哑」：Hitbox 不需要知道 Shield 存在，Shield 不需要知道怎么眩晕。想造「只闪不受护盾」的陨石就只挂 Hitbox+Health+Flash。

**事件中继（Event Relay / Bubbling）：**把底层通用事件翻译成高层语义事件，由中间人向上广播。

```gdscript
# enemy_spawner.gd — 中间人
class_name EnemySpawner extends Marker2D

@export var enemy_scene: PackedScene
@export var spawn_interval: float = 2.0
@export var spawn_container: Node
signal enemy_defeated(score_value: int)

func spawn_enemy() -> void:
    var new_enemy = enemy_scene.instantiate()
    var health = new_enemy.get_node_or_null("HealthComponent")
    if health:
        health.died.connect(_on_spawned_enemy_died)

    var parent_node: Node = spawn_container if spawn_container else get_parent()
    parent_node.add_child(new_enemy)
    new_enemy.global_position = global_position
    # 注意：不要把敌人 add_child 到 spawner 自己身上，否则 spawner 移动会拖走敌人

func _on_spawned_enemy_died() -> void:
    enemy_defeated.emit(100)   # 翻译成高层事件
```

```gdscript
# level_manager.gd — 只关心 spawner，不关心具体敌人
func _ready() -> void:
    $AlienSpawner.enemy_defeated.connect(_on_enemy_defeated)

func _on_enemy_defeated(score: int) -> void:
    GameManager.add_score(score)
```

**激光与 enemy 的解耦（Groups + Duck Typing）：**

```gdscript
# laser.gd
var damage_payload: float = 10.0

func _on_area_entered(area: Area2D) -> void:
    if area.is_in_group("enemy") and area.has_method("damage"):
        area.damage(damage_payload)
        queue_free()
```

> 激光不知道打中了 AlienDrone，也不知道 HealthComponent 是什么。加 50 种新敌人无需改 laser 脚本。
> **避免 magic string**：用常量 Autoload（`const GROUP_ENEMY = "enemy"`）让自动补全帮忙查拼写。

### 权衡与陷阱

| 收益 | 代价 |
|---|---|
| 逻辑只写一次、可复用 | Scene Tree 日益密集 |
| Bug 被隔离，易定位 | 传递数据更复杂（需要接线） |
| 不同行为可分给不同人并行开发 | 构建不被复用的通用组件会拖慢开发 |

**何时不用组件：**对象简单单一、只有一次性的物体、或为「将来也许需要」而设计时。遵循 **YAGNI**（别提前造）与 **DRY**（一旦重复就提取）的平衡：等第二/第三个对象真的需要同一逻辑时再提取。

---

## 6. Factory 模式（节点工厂 / Spawner）

### 核心原则
把「创建对象的责任」从**需要对象**的脚本中移出，交给一个专职**构建对象**的脚本。在 Godot 中通常实现为一个 `Node2D` 组件，即业界术语 **Spawner**（Factory 是模式名，Spawner 是实现名，二者可互换）。

### 适用场景
- 同一类对象被**多个脚本**创建（玩家、敌人、炮塔都生成激光）。
- 对象需要**多步初始化、数据注入或随机属性**。
- 对象需要被路由到**专门的容器节点**（如 `EnemyContainer`）。
- 程序化生成（小行星场、无尽敌潮）。

### 反模式
**创建逻辑散落各处（违反 DRY）：**

```gdscript
# BEFORE：每个需要生成激光的脚本都重复这段
func fire_laser() -> void:
    var laser = laser_scene.instantiate()
    get_tree().current_scene.add_child(laser)
    laser.global_position = global_position
    laser.global_rotation = global_rotation
```

为什么错：一旦要改「所有敌人加进 `EnemyContainer`」，得改二十个脚本；创建逻辑分散导致脆弱、难调试、团队协作易冲突。

**另一个反模式**：给只出现一次的对象（如最终 Boss）建专用 `BossFactory`——过度设计。

### 正确做法
**通用 Spawner 组件：**

```gdscript
# spawner.gd
class_name Spawner extends Node2D

@export var product_scene: PackedScene
@export var parent_container: Node

signal product_created(product: Node)

func spawn() -> Node:
    if not product_scene:
        push_error("No product_scene assigned!")
        return null

    var product = product_scene.instantiate()

    # 决定父容器
    var container: Node = parent_container if parent_container else get_tree().current_scene
    container.add_child(product)     # 若在 physics 回调中触发，用 call_deferred("add_child", product)

    # 对齐到 Spawner 自身的位置与旋转
    if product is Node2D:
        product.global_position = global_position
        product.global_rotation = global_rotation

    product_created.emit(product)
    return product
```

调用方只需 `$LaserSpawner.spawn()`。

**集中化的收益：**
- **单一事实来源**：改生成方式只改 Spawner。
- **解耦依赖**：调用方不需要懂激光/道具如何搭建。
- **一致的安全**：统一用 `call_deferred` 规避 physics 帧错误。
- **易扩展**：有了统一 choke point，将来给所有生成的物体注入随机属性只改一处。

**程序化生成（组合 Factory + 数学组件）：**

```gdscript
# radial_randomizer.gd — 不听数学，只监听工厂公告
extends Node

@export var spawner: Spawner
@export var min_radius: float = 100.0
@export var max_radius: float = 300.0

func _ready() -> void:
    spawner.product_created.connect(_on_product_created)

func _on_product_created(product: Node) -> void:
    if product is Node2D:
        var random_angle = randf() * TAU
        var random_distance = randf_range(min_radius, max_radius)
        var offset = Vector2(cos(random_angle), sin(random_angle)) * random_distance
        product.global_position += offset
```

于是小行星环 = Timer（循环 10 次）→ Spawner.spawn() → product_created → RadialRandomizer 重新定位。**没有专门写一行小行星脚本。**

### 权衡与陷阱

| 决策因素 | 直接脚本生成 | Factory 模式 |
|---|---|---|
| 创建复杂度 | 一两行即可 | 多步初始化/数据注入/随机属性 |
| 使用规模 | 仅一个脚本生成 | 多个脚本生成同一类对象 |
| 对象多样性 | 每次都是同一场景 | 按数据/随机/数组变化 |
| 层级管理 | 直接作为创建者子节点 | 需路由到独立容器 |
| 耦合 | 必须知道对象如何工作 | 只需拿到成品 |

- **何时不用**：原型期默认直接生成；只在第二次/第三次复制粘贴时重构为 Factory。
- **过度解耦的反面**：若发射一颗激光要穿过五个脚本和三个 Factory，反而更难调试。模式的目的是让代码更易读，不是用文件迷宫隐藏逻辑。

---

## 7. Builder 模式

### 核心原则
把**复杂对象的构建过程**与**最终表示**分离，用 **method chaining**（每个配置函数 `return self`）一步步组装。适合需要多步配置、拥有大量可选部件或嵌套子节点的对象。

### 适用场景
- **动态 UI 生成**（运行时生成几十个道具 tooltip、团队开发插件）。
- 程序化关卡、复杂对话树等需要「先搭骨架再逐层填充」的对象。
- 静态菜单（主菜单）应继续用可视化编辑器搭，不要代码生成。

> Builder 本质是一个高度特化的 Factory，多了**逐步定制**能力。

### 反模式
- 把十个参数塞进单个 `_init()`（**constructor telescoping**，如 `spawn(10.0, Color.RED, 2.0, 50)`）。
- 给只有一两个属性的简单对象硬上 Builder。

### 正确做法
**Builder（继承 `RefCounted`，不属于场景树）：**

```gdscript
# menu_builder.gd
class_name MenuBuilder extends RefCounted

var _menu_root: VBoxContainer

func _init() -> void:
    _menu_root = VBoxContainer.new()
    _menu_root.alignment = BoxContainer.ALIGNMENT_CENTER

func add_title(text: String) -> MenuBuilder:
    var label = Label.new()
    label.text = text
    label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    _menu_root.add_child(label)
    return self        # 返回 self 是链式调用的关键

func add_button(text: String, callable: Callable) -> MenuBuilder:
    var btn = Button.new()
    btn.text = text
    btn.pressed.connect(callable)
    _menu_root.add_child(btn)
    return self

func build() -> Control:
    return _menu_root    # 终止链，返回成品
```

**用 `@tool` 在编辑器内实时预览：**

```gdscript
@tool
extends Control
# autoshop_terminal.gd

@export var generate_preview: bool = false:
    set(_value):
        _build_shop_ui()

func _build_shop_ui() -> void:
    for child in get_children():
        child.queue_free()

    var upgrade_menu = MenuBuilder.new() \
        .add_title("Ship Upgrades") \
        .add_button("Upgrade Shields ($500)", _on_shield_upgrade) \
        .add_button("Upgrade Lasers ($800)", _on_laser_upgrade) \
        .build()

    add_child(upgrade_menu)
```

`\` 是 GDScript 的续行符，让链式调用可分行书写。

**中间态方案：Configuration Object（当 Factory 参数过多但还不到 Builder 复杂度时）：**

```gdscript
# 用配置对象替代 constructor telescoping
class_name ProjectileConfig extends RefCounted
var speed: float = 500.0
var color: Color = Color.WHITE
var scale: float = 1.0
var damage: int = 10

# 调用方只覆盖需要的字段
func fire_heavy_shot() -> void:
    var config = ProjectileConfig.new()
    config.color = Color.RED
    config.damage = 50
    ProjectileFactory.spawn(config)
```

适合作高度可变的对象（弹丸、粒子效果）；真正的 Builder 留给需要复杂多步结构组装的对象（程序化地牢、复杂对话树）。

### 权衡与陷阱

| 决策因素 | Factory | Builder |
|---|---|---|
| 主要目标 | 快速产出可直接使用的对象 | 逐步组装单个高配置对象 |
| 构建过程 | 一次 `spawn()`/`create()` 拿成品 | 多次链式调用后 `build()` |
| 对象复杂度 | 对象基本同构 | 有大量可选部件/嵌套子节点 |
| 封装重点 | 内存分配、层级管理、实例化样板 | 属性注入、依赖连接、结构布局 |
| 常见用途 | 生成敌人、粒子 | 程序化关卡 |
| 常见错误 | 给一次性 Boss 建专用 Factory | 给简单对象用 Builder |

**经验法则**：现在要造 100 个同类东西 → Factory；要造 1 个但需 10 个设置步骤 → Builder。

---

## 8. Command 模式

### 核心原则
把**请求/动作/行为**封装成独立对象（扩展 `RefCounted` 的轻量数据包），将「做什么」与「谁触发它」分离。四个角色：**Client**（产生请求）、**Invoker**（路由请求）、**Command**（封装的数据对象）、**Receiver**（最终执行者）。

### 适用场景
- 需要**自定义按键映射**（把动作当变量替换）。
- 想让**AI 与玩家共用同一套字符脚本**（AI 生成同样的 Command 对象）。
- **输入缓冲、动作队列**（策略游戏排产、动作游戏同帧执行多动作）。
- **回放/宏**（记录 Command 流而非视频）。
- **Undo/Redo**（谜题、策略游戏）。

### 反模式
**把输入硬编码进角色脚本（invoker 与 receiver 死结）：**

```gdscript
func handle_input() -> void:
    if Input.is_action_pressed("button_x"):
        jump()                 # 意图与执行绑死，无法重映射
    elif Input.is_action_pressed("button_y"):
        fire_weapon()
```

为什么错：改键、AI 控制、混淆弹（打乱输入）都得写扭曲的代码。

**命令内部硬找玩家：**若 Command 硬编码去寻找 player，则它完全无法用于敌人 NPC。

### 正确做法
**Base Command + 具体 Command（把 Receiver 传入，而非内部搜树）：**

```gdscript
class_name Command extends RefCounted
var command_name: String

func execute(actor: Node) -> void:
    pass
```

```gdscript
class_name ShootCommand extends Command

func execute(actor: Node) -> void:
    if actor.has_method("fire_blaster"):
        actor.fire_blaster()
```

```gdscript
# Invoker：只产生命令，不执行（因为还不知道该作用于谁）
class_name PlayerInputHandler extends Node

func get_command() -> Command:
    if Input.is_action_pressed("fire_weapon"):
        return ShootCommand.new()
    elif Input.is_action_pressed("deploy_shield"):
        return ShieldCommand.new()
    return null
```

```gdscript
# 主循环里把命令交给具体 actor
class_name PlayerController extends Node

@export var player_actor: CharacterBody2D
@onready var input_handler: PlayerInputHandler = $PlayerInputHandler

func _physics_process(delta: float) -> void:
    var command: Command = input_handler.get_command()
    if command:
        command.execute(player_actor)
```

**AI 复用同一架构：**AI 逻辑不响应键鼠，而是直接生成并派发 Command 到同一条流。把「选择动作的大脑」与「执行动作的身体」分离，就能热换 AI 档案，甚至把 AI 接到玩家身上做自动测试/演示回放。

**命令队列（顺序执行）：**

```gdscript
class_name CommandUnit extends Node2D

var command_q: Array[Command] = []
var history_q: Array[Command] = []
var awaiting_execution: bool = false
const MAX_HISTORY: int = 50

func add_command(c: Command) -> void:
    command_q.append(c)
    execute_next_command()

func execute_next_command() -> void:
    if awaiting_execution or command_q.is_empty():
        return
    awaiting_execution = true

    var c: Command = command_q.front()
    if is_instance_valid(self):          # 防止 receiver 已被删除
        await c.execute(self)            # 派生命令内的 await 使其成为协程

    command_q.pop_front()
    history_q.push_front(c)

    if history_q.size() > MAX_HISTORY:   # 防止历史无限增长
        history_q.pop_back()

    awaiting_execution = false
    execute_next_command()               # 递归继续
```

**常见陷阱：**
- **悬空引用（状态失同步）**：命令被延迟执行，执行前 receiver 可能已被销毁 → 执行前 `is_instance_valid()`。
- **无限历史（内存泄漏）**：历史数组持续增长 → 设 `MAX_HISTORY` 上限并 `pop_back()`。
- **阻塞队列**：命令内部若不结束（等一个被删的 UI 动画），`await` 会永久挂起整个队列 → 保证命令有确定的退出条件。

**Undo/Redo：**让每个命令既知道如何执行、也知道如何逆转。

```gdscript
class_name MoveCommand extends Command

var initial_position: Vector2
var target_position: Vector2

func _init(target: Vector2) -> void:
    command_name = "Move"
    target_position = target

func execute(actor: Node) -> void:
    initial_position = actor.global_position      # 缓存起始状态
    var tween: Tween = actor.create_tween()       # 命令不是 Node，不能自己创建 Tween
    tween.tween_property(actor, "position", target_position, 0.5)
    await tween.finished

func undo(actor: Node) -> void:
    var tween: Tween = actor.create_tween()
    tween.tween_property(actor, "position", initial_position, 0.5)
    await tween.finished
```

Undo 三步：从 `history_q` **pop** → `await command.undo(actor)` → **push** 到 `redo_q`。
行业标准：玩家 undo 后又执行新动作时，清空 redo 队列（`redo_q.clear()`），即新时间线覆盖旧未来。

**动作游戏：并行执行（不阻塞）：**

```gdscript
func _physics_process(delta: float) -> void:
    var move_cmd = input_handler.get_move_command()
    if move_cmd:
        move_cmd.execute(player_actor, delta)   # 立即改速度，无 await

    var shoot_cmd = input_handler.get_shoot_command()
    if shoot_cmd:
        shoot_cmd.execute(player_actor)         # 立即生成激光
```

因为动作是解耦的数据包，不必强行塞进单个阻塞队列——移动与开火可在同一帧各自独立触发，互不干扰。

### 权衡与陷阱
- 严格的 `await` 队列适合回合制/策略/谜题，不适合实时动作游戏（否则「移动动画未播完就开不了枪」）。
- 命令是轻量数据包，不要扩展 `Node`（每次按键生成 Node 会严重内存膨胀）。
- 队列引入了基于时间的复杂度（见上「常见陷阱」）。

---

## 9. Service 模式（横切系统）

### 核心原则
把**每个对象几乎都要用到**的横切关注点（cross-cutting concerns：播放音效、存读档、埋点日志）集中到全局 Service，并让 Service **尽可能无状态**：执行任务、然后立刻忘记数据。

### 适用场景
- 音频管理、存档系统、成就、分析埋点等游戏级系统。
- 需要**替换实现而不改玩法逻辑**（本地存档 → 云存档）。

### 反模式
两种常见极端：
1. **给每个实体挂冗余节点**（每个敌人自带 `AudioStreamPlayer`）：膨胀场景树、浪费内存。且若敌人调用自身音频后立即 `queue_free()`，音频会被一起销毁，爆炸声突兀中断。
2. **紧密耦合到全局变量**：脚本变僵硬脆弱。

**有状态的 Spaghetti Global（错误示范）：**

```gdscript
# BAD：Autoload 囤积了本属于其他对象的数据
extends Node

var player_health: int = 100
var current_score: int = 0
var inventory: Array = []

func take_damage(amount: int) -> void:
    player_health -= amount
```

为什么错：任何脚本都能随时改玩家血量，无法追踪；全局脚本承担了本属于玩家自己的职责。

### 正确做法
**无状态 Service：**

```gdscript
# GOOD：执行任务后立即忘记
extends Node

func save_game_state(health: int, score: int, inv: Array) -> void:
    var save_dict := {"health": health, "score": score, "inventory": inv}
    var file = FileAccess.open("user://save.dat", FileAccess.WRITE)
    file.store_string(JSON.stringify(save_dict))
    file.close()
```

**带对象池的 AudioService（避免音效被调用者销毁而中断）：**

```gdscript
# audio_service.gd (Autoload 命名为 'Audio')
extends Node

var _audio_pool: Array[AudioStreamPlayer] = []
const POOL_SIZE: int = 10

func _ready() -> void:
    for i in range(POOL_SIZE):
        var player := AudioStreamPlayer.new()
        add_child(player)
        _audio_pool.append(player)

func play_sound(stream: AudioStream) -> void:
    for player in _audio_pool:
        if not player.playing:
            player.stream = stream
            player.play()
            return                       # 尽早退出
    push_warning("Audio pool is full! Sound dropped.")
```

**保持调用方易移植（不硬编码全局，运行时探测服务）：**

```gdscript
func die() -> void:
    var audio_service: Node = get_node_or_null("/root/Audio")
    if audio_service and audio_service.has_method("play_sound"):
        audio_service.play_sound(explosion_sfx)
    queue_free()   # 音效交给全局播放，自身可立即删除
```

这样敌人脚本可以搬到没有 Audio Autoload 的其他项目而不编译失败。

### 权衡与陷阱
- Service 应无状态；若一个 Autoload 同时存玩家血量、分数、背包，它就是 Spaghetti Global 而非干净 Service。
- 用 `get_node_or_null` + `has_method` 动态探测会牺牲一点静态类型安全与自动补全，换取可移植性；在项目内部则可考虑接口（`@abstract`）与 Setter 注入来兼顾。

---

## 10. 用 Command/Service 做隔离测试

### 核心原则
解耦架构的最大隐藏收益：**可以在不启动整个游戏引擎和场景的前提下，秒级运行自动化测试。** 因为逻辑已从物理节点中剥离，可用轻量 mock/dummy 替身验证行为。

### 适用场景
- 验证 Command 的数学（如移动时长）。
- 验证失败路径（如空历史队列下狂按 Undo）。
- 测试玩法逻辑时不想让上百个真实爆炸音效炸响扬声器。

### 正确做法
**用 mock actor 测 Command：**

```gdscript
class_name MockShip extends Node2D    # 只需 global_position，无需碰撞/精灵/相机

func test_duration_calculation() -> void:
    var ship := MockShip.new()
    ship.global_position = Vector2.ZERO

    var move_cmd := MoveCommand.new()
    move_cmd.unit = ship
    move_cmd.speed = 100.0
    move_cmd.target_position = Vector2(500.0, 0.0)

    move_cmd.execute()

    if move_cmd.get_duration() == 5.0:   # 500 / 100 = 5.0
        print("Test Passed: Duration calculation is correct.")
```

**测试失败场景（guard clause）：**

```gdscript
func test_empty_undo_queue() -> void:
    var command_manager = CommandUnit.new()
    command_manager.undo_last_command()      # 历史为空，应被 guard clause 拦下
    if command_manager.awaiting_execution == false:
        print("Test Passed: Guard clause safely caught the empty queue.")
```

**用 Mock Service 做静默测试：**

```gdscript
# MockAudioService：不触碰音频引擎，只记录「本应播放」
# 替换真实 AudioService 后跑战斗测试
if move_cmd.get_duration() == 5.0:
    pass
```

收益：即使将来真实音频因引擎更新坏掉，用 MockAudioService 的玩法测试依然能通过——**证明核心玩法逻辑完好，Bug 被隔离在音频实现内**。

### 权衡与陷阱
- Mock 与真实实现的契约要一致（方法名/签名），否则测试通过但真实运行失败。
- 隔离测试覆盖行为意图与关键失败条件；无法覆盖的部分需说明残余风险。

---

## 快速抉择表（综合）

| 遇到的情况 | 推荐方案 |
|---|---|
| 追踪心情/阶段（Idle → Chase → Attack） | State 模式 |
| 追踪同一任务的不同算法（激光/导弹/护盾） | Strategy 模式 |
| 庞大条件块（`if/else` 或 `match` 超 50 行） | 重构为 State/Strategy |
| 简单二元开关（门开/关） | 普通 Boolean，不要模式 |
| 跨系统一次性事件（死亡、得分） | Event Bus（Event Out） |
| 需要持久、多订阅的状态（血量、弹药） | Observable Resource + Push/Pull |
| 底层物理事件 → 高层语义事件 | Event Relay / Bubbling |
| 需要在无 UI / 独立场景中复用底层对象 | Signal Up + 中间人接线 |
| 当前要造 100 个同类对象 | Factory / Spawner |
| 当前要造 1 个但需 10 步配置 | Builder |
| 大量同构对象 + 少量可选参数 | Factory + Configuration Object |
| 攒同构实体共享重叠行为 | Component（组合优于继承） |
| 需要改键 / AI 与玩家共用角色 / 回放 / Undo-Redo | Command 模式 |
| 全局横切系统（音频、存档、埋点） | 无状态 Service（Autoload） |
| 想秒级自动化测试玩法逻辑 | Command + Mock Service |

> **贯穿全篇的元原则**：先简单，等到「复制粘贴」或「条件膨胀」的痛苦真实出现（YAGNI ↔ DRY 的交点）再引入模式。模式的目的是让代码更易读、更易改，而不是用文件迷宫隐藏逻辑。
