# 场景与节点架构参考

> 本文档提炼自《Godot 4 Best Practices》第 2 章 (Deciding Between Scenes and Scripts)、第 3 章 (Organizing Scenes for Scalability)、第 4 章 (When Not to Use Nodes)。

Godot 是"不表态"的引擎：它不强制任何架构。因此"用什么、放哪里"的判断权完全在开发者手中，而早期错误决策往往在项目后期才以性能瓶颈和难以重构的形式暴露。本文档给出这三章的可操作原则。

---

## 第 2 章：场景 vs 脚本的决策

### 2.1 核心区分：声明式结构 vs 命令式行为

**核心原则**：场景是声明式的，描述"有什么"（结构）；脚本是命令式的，描述"怎么做"（行为）。

**适用场景**：
- 场景（`.tscn`）：UI 布局、游戏对象（Player/Enemy）、关卡、任何需要可视化组装或复用的结构。
- 脚本（`.gd`）：数据计算、存档系统、状态机、工具逻辑，不需要视觉呈现的系统。

**反模式**：在 `_ready()` 里用代码手动 `Node.new()`、设属性、逐个 `add_child()` 来搭建固定结构。

```gdscript
# Bad: 忽略引擎优势，逐行构建且难以维护
func _ready():
    var sprite = Sprite2D.new()
    sprite.texture = load("res://player.png")
    sprite.position = Vector2(0, 0)
    add_child(sprite)
```

**正确做法**：固定结构在 Scene dock 中声明，脚本只负责行为。

```gdscript
# Good: 结构在 .tscn 中声明，脚本只处理输入与行为
extends RigidBody2D
@export var speed = 500

func _physics_process(delta):
    var movement = Vector2.ZERO
    if Input.is_action_pressed("paddle_1_down"):
        movement = Vector2.DOWN
    elif Input.is_action_pressed("paddle_1_up"):
        movement = Vector2.UP
    linear_velocity = movement * speed
```

**权衡与陷阱**：`.tscn` 是纯文本（text scene），可读、对 Git 友好，但也"啰嗦"。若把易变数据或复杂逻辑塞进场景属性，diff 会变得难以审阅——**易变的系统应交给脚本**。

| 维度 | Scene (`.tscn`) | Script (`.gd`) |
| --- | --- | --- |
| 主要职责 | 结构与视觉 | 行为与逻辑 |
| 思维模型 | 声明式（是什么） | 命令式（做什么） |
| 最适合 | UI 布局、游戏对象、关卡 | 数据处理、计算、存档、状态机、工具 |
| 继承方式 | 视觉继承（变更向子级传播） | 逻辑继承（共享函数/变量） |
| 性能 | 内存开销较高（跟踪 transform、可见性） | 轻量（`Object`/`RefCounted`）或标准（`Node`） |

### 2.2 场景的实例化成本与加载策略

**核心原则**：场景"存储"很便宜，"实例化"很昂贵——应避免在游戏进行中同步加载。

**适用场景**：任何在运行时生成的对象（子弹、敌人、关卡切换）。

**反模式**：在按键回调里 `load()` 并 `instantiate()`，造成帧卡顿。

```gdscript
# Bad: 按下按钮的瞬间才解析文件，导致掉帧
func fire_laser():
    var laser = load("res://laser.tscn").instantiate()
    add_child(laser)
```

**正确做法**：用 `preload()` 在脚本解析期（通常是加载界面）就完成文件读取。

```gdscript
# Good: 脚本初始化时即预加载
const LASER_SCENE = preload("res://laser.tscn")

func fire_laser():
    var laser = LASER_SCENE.instantiate()
    add_child(laser)
```

**权衡与陷阱**：
- `preload()` 要求**静态字符串**。需要动态路径（如 `"res://levels/" + name + ".tscn"`）时必须用 `load()`。
- `preload()` 会**立即占用内存**。巨大的隐藏 Boss / 后期过场不应预加载，会浪费 RAM。
- 小游戏 / 原型：场景只有几十个节点时实例化在亚帧级完成，**优先用简单的同步加载**，不要过度工程化。
- 超大场景（整个关卡、密集 3D 城市）：`preload()` 仍会在加载界面冻结——需用 `ResourceLoader` **后台线程异步加载**（三步：`load_threaded_request()` → `load_threaded_get_status()` 轮询并更新进度条 → `load_threaded_get()` 取回并实例化）。

```gdscript
var next_level_path = "res://Levels/Level_2.tscn"

func _ready() -> void:
    ResourceLoader.load_threaded_request(next_level_path)

func _process(_delta: float) -> void:
    var progress = []
    var status = ResourceLoader.load_threaded_get_status(next_level_path, progress)
    match status:
        ResourceLoader.THREAD_LOAD_IN_PROGRESS:
            print("Loading: ", progress[0] * 100, "%")
        ResourceLoader.THREAD_LOAD_LOADED:
            var level_scene = ResourceLoader.load_threaded_get(next_level_path)
            get_tree().current_scene.add_child(level_scene.instantiate())
            set_process(false)
        ResourceLoader.THREAD_LOAD_FAILED, ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
            push_error("Background load failed.")
            set_process(false)
```

### 2.3 何时用独立脚本（无节点）

**核心原则**：纯逻辑系统应扩展轻量类（`RefCounted` / `Resource`），而不是塞进 Scene Tree 里的隐形节点。

**适用场景**：
- `RefCounted`：临时逻辑（数学计算器、工具类），引用计数归零自动释放，无内存泄漏。
- `Resource`：需要存盘（`.tres`）的被动数据（敌人属性、物品、配置）。

**反模式**：为存档功能建一个空的 `Node` 挂脚本，只为了"能在场景里找到它"——引入了无意义的 Scene Tree 开销。

**正确做法**：用静态 `RefCounted` 脚本，全局可用且零节点开销。

```gdscript
class_name SaverLoader extends RefCounted

static func save_game(player_health: int) -> void:
    var file = FileAccess.open("user://savegame.data", FileAccess.WRITE)
    file.store_var(player_health)
    file.close()

static func load_game() -> int:
    var file = FileAccess.open("user://savegame.data", FileAccess.READ)
    var player_health: int = file.get_var()
    file.close()
    return player_health
```

**权衡与陷阱**：脚本与场景并非二选一。`class_name` 让脚本进入编辑器的 **Create New Node** 对话框，成为"脚本节点"，可像内置节点一样拖入 Scene Tree，这是打通两者的桥梁。

### 2.4 `@tool`：让脚本在编辑器里运行

**核心原则**：`@tool` 注解让脚本在编辑器内也执行，可用于可视化调试与数据校验。

**适用场景**：
- 可视化调试：为 `range` 变量在编辑器中画出攻击范围圈。
- 数据校验：用 `_get_configuration_warnings()` 检测缺失的必需节点。

```gdscript
@tool
extends Node2D

@export var radius: float = 100.0:
    set(value):
        radius = value
        queue_redraw()

func _draw() -> void:
    if Engine.is_editor_hint():
        draw_circle(Vector2.ZERO, radius, Color(1, 0, 0, 0.3))
```

**权衡与陷阱**：`@tool` 代码会同时在编辑器和运行时执行，务必用 `Engine.is_editor_hint()` 隔离仅在编辑器生效的逻辑，避免运行时出现意外副作用。

### 2.5 继承场景 vs Resource 组件：平衡组合与继承

**核心原则**：**继承场景（Inherited Scene）用于视觉特化；脚本继承用于逻辑特化；组合（组件 / Resource）用于功能追加。**

**适用场景**：
- 继承场景：同一原型的多个视觉变体（`Goblin` / `Orc` 共享 `BaseEnemy` 结构）；UI 换肤（`ConfirmButton` / `CancelButton` 继承 `BaseButton`）。共同点是 **Is-A**（视觉与配置差异，逻辑一致）。
- Resource 组件：**Has-A** 关系（Goblin *has a* `HealthComponent`），能力可跨不相关对象复用（Player / Crate 都能受伤）。

**反模式**：为每种敌人写一个近乎相同的子类脚本，深度继承链导致"意大利面式继承"；或纯手工组合 50 个敌人场景，改一次碰撞层要编辑 50 个文件。

**正确做法**（Resource 组件 + Inspector 注入）：

```gdscript
# attack_component.gd —— 组件基类
class_name AttackComponent extends Resource

func attack() -> void:
    print("Default attack")
```

```gdscript
# tnt_attack.gd —— 具体行为，保存为 tnt_attack_component.tres
class_name TntAttackComponent extends AttackComponent

func attack() -> void:
    print("Throws dynamite")
```

```gdscript
# Enemy.gd —— 通过 @export 注入，而非 $Path 引用
class_name Enemy extends CharacterBody2D

@export var attack_component: AttackComponent

func perform_attack() -> void:
    attack_component.attack()
```

**关键细节**：用 `@export var attack_component: AttackComponent` 而不是 `@onready var attack_component = $AttackComponent`。导出变量不绑定 Scene Tree 路径，组件可以在树中任意位置、甚至只是资源文件；设计师重命名节点也不会破坏引用。

**权衡与陷阱（Resource 共享陷阱）**：Godot 中 Resource **默认按引用共享**。十个 Goblin 共享同一个 `HealthComponent` 实例时，一个受伤会导致全部受伤。两种解法：

```gdscript
# 方案一：编辑器里勾选 Local to Scene（每个场景实例自动复制）

# 方案二：代码中 duplicate() —— 共享只读模板，复制易变数据
@export var base_stats: Resource      # 共享模板
var current_stats: Resource

func _ready() -> void:
    current_stats = base_stats.duplicate()
```

- 静态只读数据（武器基础伤害）→ 共享同一个 Resource。
- 运行时易变状态（当前血量）→ `duplicate()`。

**其他权衡**：
- 组件/Resource 方案前期成本高，对小型项目或 Game Jam 是过度设计。
- 一次性、高度特化的 Boss 机制，单独脚本通常更简单。
- 推荐迭代节奏：**先原型后架构**（prototype first, architect second）——先用 GDScript 快速硬编码找到乐趣，当发现同一行为要套用到十个敌人时，才是抽取组件的信号。

| 维度 | 继承（`extends`） | 组合（组件 / Resource） |
| --- | --- | --- |
| 关系 | Is-A（Goblin *is an* Enemy） | Has-A（Goblin *has a* HealthComponent） |
| 灵活性 | 刚性，改基类影响整条链 | 灵活，可混搭（Attack 换成 Heal） |
| 复杂度 | 起步简单，深层树变复杂 | 前期配置多，可无限扩展 |
| 复用性 | 限于特定类层级 | 高，HealthComponent 可用于 Player/Enemy/Crate |
| 何时用 | 对象共享根本身份 | 对象共享能力但身份不同 |

**Inspector 可读性**：导出变量变多时用注解分组，这既是团队协作界面，也是给未来自己的自文档。

```gdscript
@export_group("My Properties")
@export var first_property = 1
@export_subgroup("Additional Properties")
@export var flag = false
@export_category("Primary Category")
@export_range(0, 20) var i
```

### 2.6 混合方案

**核心原则**：大多数真实项目是场景 + 脚本的混合，而非纯场景或纯脚本。

**示例**（复杂武器系统）：

- **Scene**（`assault_rifle.tscn`）负责"物理存在"：`Sprite2D`、`AudioStreamPlayer`、子弹生成点的 `Marker2D`，只管表现。
- **Resource**（`rifle_stats.tres`）负责数据：射速、伤害、弹数，设计师可在 Inspector 调平衡。
- **Pure Script**（`ballistics.gd`）负责逻辑：独立脚本，含弹道下坠与风阻公式，不挂在任何节点上。

**权衡与陷阱**：不要为了"纯粹"强行把整个系统塞进单一场景或单一脚本，混合才能各取所长。

---

## 第 3 章：面向可扩展性的场景组织

### 3.1 场景模块化

**核心原则**：每个场景应是自包含单元，不重度依赖运行环境——能按 `F6` 单独运行而不崩溃。

**适用场景**：所有可复用的游戏对象（`PlayerShip`、`EnemyDrone`、`CockpitUI`）。

**反模式**：靠硬编码路径寻找邻居，导致场景脱离特定位置就报 null。

```gdscript
# Bad: 依赖树中特定位置，移动节点即崩溃
func take_damage(amount: int) -> void:
    health -= amount
    get_node("../CockpitUI/HealthBar").update_health(health)
    get_node("../GameManager").check_game_over()
```

**正确做法**：用信号广播自身状态，不关心谁在监听。

```gdscript
# Good: 只广播状态，不知道 UI 是否存在
class_name PlayerShip extends CharacterBody2D

signal hull_damaged(amount)
var health: int = 50

func take_damage(amount: int) -> void:
    health -= amount
    hull_damaged.emit(health)
```

**权衡与陷阱**：模块化的收益是解耦、可复用、可独立测试；代价是需要显式建立信号连接。对**同一封装场景内部**的父子节点，直接引用反而是正确的（见 3.4）。

### 3.2 规则一：保持场景浅层级

**核心原则**：深层嵌套是坏信号——每多一层就增加耦合与调试难度。

**适用场景**：游戏对象与关卡道具应严格保持浅层级。

**反模式**：把引擎的每个粒子发射器、音效都直接塞进 `PlayerShip`，导致 `player_ship.gd` 变成处理无关逻辑的上帝类。

**正确做法**：把大型系统拆成可组合的子场景。`Engine` 应是独立场景（含推进器精灵和音效），由 Ship 在需要时实例化——这样同一个 `Engine` 场景可复用于敌方战机、友方无人机，无需复制逻辑。

**权衡与陷阱（唯一例外）**：**UI 是合理的例外**。复杂响应式菜单常需要深层容器链（`MarginContainer → VBoxContainer → Panel → HBoxContainer`）才能正确处理自动缩放。这是可接受的，因为这些节点**纯用于视觉定位，不含逻辑**。游戏对象则必须遵守浅层级规则。

### 3.3 解决深层 UI 的引用问题：Export 变量与场景唯一节点

**核心原则**：避免用长而脆弱的节点路径访问深埋节点。

**反模式**：

```gdscript
# Bad: 把 Label 移出 Container 就断链
get_node("UI/Container/Label")
```

**正确做法（两种）**：

```gdscript
# 方案一：@export —— 不依赖路径或字符串名
@export var shield_label: Label

# 方案二：Scene Unique Nodes（右键节点 → Access as Unique Name，标记为 %）
@onready var shield_bar: ProgressBar = %ShieldBar
```

**权衡与陷阱**：`@export` 适合少数关键引用；若场景内部组件有几十个，全部导出会塞满 Inspector 且设计师可能误清空内部引用。**纯内部引用用场景唯一节点（`%`）更合适**——即使把节点拖到场景内任意位置，引用依然有效，可放心重构视觉层级。

### 3.4 规则二：实例化复用

**核心原则**：重复出现的节点结构应成为独立场景。

**适用场景**：`Fuel Canister`、`Pause Menu` 等被多个场景复制的结构。

**反模式**：手动把 `Fuel Canister` 结构复制粘贴到 50 个关卡；日后改一次拾取音效就要打开 50 个关卡逐一手改——极易出错、维护噩梦。

**正确做法（运行时实例化）**：预加载弹体场景，运行时 `instantiate()` 后挂到主世界（**不是飞船**，否则子弹会跟着飞船移动）。

```gdscript
extends Node2D

var laser_scene = preload("res://Projectiles/Laser_Blue.tscn")

func fire_weapon():
    var new_laser = laser_scene.instantiate()
    # 关键：挂到主世界而非飞船，否则子弹随飞船移动
    get_tree().root.add_child(new_laser)
    new_laser.global_position = global_position
```

**权衡与陷阱**：静态对象（固定的门、Boss）可在编辑器直接拖放；运行时实例化只用于**无法预先放置**的动态内容（弹体、掉落物、敌潮）。

**实例化 vs 继承场景**（两者不是同一问题的竞争方案）：

| 策略 | 最适合 | 原因 | 示例 |
| --- | --- | --- | --- |
| 实例化（组合） | 组合不同功能，或放置同一对象的多个副本 | 拼装独立部件 | 关卡放陨石；把 Laser Cannon 挂到 PlayerShip |
| 继承场景（特化） | 由通用对象派生具体变体，共享逻辑 | 只覆盖差异 | 从 BaseEnemy 派生 Fast Interceptor / Heavy Bomber |

### 3.5 规则三：场景间松耦合 —— Call Down, Signal Up

**核心原则**：跨场景通信优先用**信号**，而非直接引用；方向遵循 **"Call Down, Signal Up"**。

**适用场景**：不同、不相关场景之间的通信（Player 与 UI、Game Manager）。

**反模式**：Player 直接调用 UI 和 GameManager 的方法（见 3.1 代码），移动节点即断链，Player 无法独立复用或单独测试。

**正确做法（循环信息流）**：
- **Call Down**：父节点知道自己有哪些子节点，可以安全地 `shield.activate()`。
- **Signal Up**：子节点对 owner 一无所知，只 `emit` 事件（"Shield Depleted!"），谁在听谁响应。
- **兄弟节点**：绝不互相直接引用。`WeaponComponent` 装备重武器想减速时，应先 **Signal Up** 给父节点 `PlayerShip`，父节点再 **Call Down** 让 `MovementComponent` 调速度。父节点充当管理者，保持兄弟完全解耦。

**监听端通过 @export 注入引用，避免脆弱路径**：

```gdscript
# HealthUI 脚本
extends Control

@export var player_node: Node2D   # 在 Inspector 中拖入 PlayerShip

func _ready() -> void:
    if player_node:
        player_node.hull_damaged.connect(_on_player_hull_damaged)

func _on_player_hull_damaged(new_health: int) -> void:
    color_rect.size.x = new_health
```

**权衡与陷阱（何时不该用信号）**：**直接引用在节点本质上相互依赖、且严格处于同一封装场景内时，是完全正确且常常更优的**。父脚本对子节点调用 `blaster.fire()` 是正确的——blaster 是飞船内部结构的一部分，这种紧耦合是有意为之且安全的。只有当跨越不相关的场景时才变成危险的反模式。

信号连接的额外优势：解耦、可扩展（多个监听者可连同一信号，如音效管理器也可监听 `hull_damaged`）、重构安全（重排 Scene Tree 不会破坏任何东西）。对动态对象，推荐在 `_ready()` 中用代码连接信号而非编辑器连线——一目了然、与逻辑就近。

### 3.6 用 Groups 简化管理

**核心原则**：**Hierarchy（层级）定义空间归属，Groups（分组）作为逻辑标签**。用层级构建对象，用分组进行逻辑归类。

**适用场景**：管理节点集合（所有敌人、所有可收集物、所有可交互对象）。

**反模式**：用 `call_group` 做广播——它依赖"魔法字符串"，无人能保证组内每个节点都恰好有同名、同参数的方法，且 IDE 无法追踪，重构困难。

```gdscript
# 便捷但危险：依赖字符串方法名，IDE 无法追踪
get_tree().call_group("Destructible", "take_hit", 100)
```

**正确做法**：

```gdscript
# 成员注册（Asteroid.gd）
func _ready() -> void:
    add_to_group("Destructible")

func take_hit(amount: int) -> void:
    health -= amount
```

复杂广播优先用全局 `EventBus`（Autoload），监听者在 `_ready()` 中建立**类型安全的信号连接**；`call_group` 只适用于简单状态（如暂停所有敌人）。

**权衡与陷阱（命名与定位）**：
- 组名保持语义化、非技术化：用 `Collectibles` / `Destructible`，而不是 `Group1`。
- 每组单一概念（一个节点可属于多个组，但每个组仍应代表一个概念）。
- **不要用分组替代良好的场景结构**——分组是逻辑层关系，不是层级。

**大规模系统中的典型用途**：多人实体更新同步；环境触发器统一响应同一事件；场景切换时显隐 UI 元素；统一调节所有音源音量（拖动滑块即可，无需持有每个 AudioStreamPlayer 的引用）。

### 3.7 命名约定

**核心原则**：一致性让结构可即时理解（新人和半年后的自己都能读懂）。

**关键约定**：
- **按角色加前缀节点名**：`UI_`、`Enemy_`、`Menu_`、`Btn_`、`Lbl`——用于在脚本编辑器中快速区分同类名（如 `health` 变量 vs `HealthLbl` 标签）。
- **文件用 `snake_case`**：场景（`main_menu.tscn`）、脚本（`enemy_controller.gd`）。
- **场景根节点保持 `PascalCase`**（`MainMenu`），与 Godot 原生类命名一致。
- **文件名与类名对齐**：`enemy_controller.gd` 应定义 `class_name EnemyController`，保证全局搜索和 Quick Load 可预测。

**权衡与陷阱**：命名本身不解决组织问题；它依赖全队遵守同一套规则，否则收益归零。

### 3.8 项目文件夹组织

**核心原则**：**Predictability over Preference**（可预测性优先于个人偏好）。文件夹结构的首要职责是降低所有人的认知负担。

**Type-Based 组织策略**（按类型，广泛推荐）：
- `Assets/`：原始导入数据（`.png`、`.wav`、字体），无逻辑。
- `Scenes/`：组装好的 `.tscn`，子目录按类别（Levels、UI、Characters）。
- `Scripts/`：`.gd` 逻辑文件，结构与 `Scenes/` 镜像，方便 VS Code 等外部编辑器导航。

**反模式**：没有严格层级，`res://` 变成杂物抽屉；文件数上百后无法定位资源；出现"cluttered-drawer effect"——美术改精灵要翻代码，程序员重构脚本可能误删源素材。

**权衡与陷阱**：Type-Based 还是 Feature-Based（把所有 Goblin 相关文件放一个文件夹）都可以，**最关键的是全队遵循同一模式**。任何成员都不应在"文件放哪 / 去哪找"上消耗心力。

### 3.9 避免 Scene Tree 膨胀

**核心原则**：目标不是"节点尽可能少"，而是**每个节点有清晰、单一的目的**。

**膨胀症状**：作为"容器"挂几十个子节点的节点；每帧重载的复杂场景（而非使用子场景）；兄弟间深层嵌套的信号或硬编码依赖。

**预防策略**：

```gdscript
# 1. 动态加载与释放：用完立即销毁
extends Area2D

func _on_body_entered(body: Node2D) -> void:
    if body.is_in_group("player"):
        body.collect_scrap(1)
        queue_free()
```

- **用信号和分组解耦依赖**：避免持有每个特定节点的硬引用（如 `get_node("Player")`）；判断 `body.is_in_group("player")` 比判断名字安全。
- **把静态/配置数据移入 Resource**：不要用 Node 存 RPG 属性、物品列表、游戏设置——`.tres` 更省内存且不占用 Scene Tree。
- **定期重构**：单节点开始承担过多职责（如 Player 同时处理输入、移动、背包 UI）即是膨胀信号，应把逻辑抽到子场景或独立脚本。

**排查表**：

| 症状 | 诊断 | 方案 |
| --- | --- | --- |
| 无尽滚动 | Scene Tree 过长，难以定位节点 | **模块化**：把独立分支（UI、环境）拆成 `.tscn` 再实例化回来 |
| 路径断裂 | 移动 UI 元素就报 `null instance` | **解耦**：用场景唯一节点（`%Bar`）或信号替换硬编码路径 |
| 复制粘贴疲劳 | 手动改 50 个副本的同一属性 | **继承**：建 Base 场景，改为继承场景 |
| 加载缓慢 | 关卡加载时上千对象同时生成造成冻结 | **运行时实例化**：不要全部放在编辑器里，用代码按需 `instantiate()` |

---

## 第 4 章：何时不用节点

> Godot 的口号"Everything is a Node"特指 **Scene Tree**，而非你的整个代码库。

### 4.1 节点滥用的识别与 Inventory Node 反模式

**核心原则**：节点是为模拟、渲染、Scene Tree 处理设计的**重量级**对象，携带 transform、暂停模式、物理回调、信号连接的开销。用节点存抽象数据等于为用不到的功能付出巨大代价。

**适用场景**：判断某系统是否属于 Scene Tree，问三个问题——
1. 该对象需要在屏幕上绘制什么吗？
2. 该对象需要物理碰撞吗？
3. 该对象需要存在于空间层级（父/子 transform）中吗？

三个都为 **No**，就不该是节点。（少数例外：依赖 Scene Tree 内部系统的工具节点，如需要场景时钟的 `Timer`、需要音频总线的 `AudioStreamPlayer`、需要逐帧循环驱动属性的 `AnimationPlayer`。）

**反模式**：用 Scene Tree 当数据库——"容器节点"里挂着的子节点唯一用途是持有变量数据。

```gdscript
# CargoHold.gd（反模式）—— 把数据存储与场景实例化混为一谈
extends Node2D

func add_item(item_scene: PackedScene):
    var new_item = item_scene.instantiate()
    add_child(new_item)
    print("Added " + new_item.item_name)

func get_items():
    return get_children()
```

**为什么错（不可扩展的四个原因）**：
- **内存开销**：背包里每件物品都是节点，必须跟踪树中位置、检查 `_process`、监听输入，尽管它只是虚拟背包里的数据。
- **存档复杂**：不能只存数据，必须遍历子节点、读属性、序列化为 JSON，加载时再重新实例化各自的场景。
- **依赖纠缠**：检查是否有某物品要用 `get_node()` 或遍历子节点；若游戏逻辑在节点入树前运行，背包就会出错。
- **渲染 vs 数据混淆**：UI 关闭时这些节点仍在内存；删除节点数据就丢失，**迫使你为了保留物品而让 UI 常驻**。

### 4.2 轻量对象层级

**核心原则**：沿继承树从 `Node` 向下走向 `Object`，剥离渲染与物理开销，只保留需要的数据与逻辑能力。

| 类 | 使用场景 | 内存管理 | Inspector | 可序列化 |
| --- | --- | --- | --- | --- |
| `Object` | 极致性能、临时数据 | 手动 `free()` | 否 | 否 |
| `RefCounted` | 数学计算器、逻辑管理器、状态机 | 自动 | 否 | 否 |
| `Resource` | 物品、属性、可配置数据、存档 | 自动 | 是 | 是 |
| `Node` | 渲染、物理、场景层级 | 自动 `queue_free()` | 是 | 部分 |

- **`Object`**：最底层，快且省内存，但需手动管理。创建后必须显式 `free()`，否则常驻内存；若变量引用了已被别处删除的 `Object` 会变成悬垂指针，访问即崩溃。仅在需要极致性能的临时数据结构且能驾驭手动内存管理时使用。Godot 自身就用它实现高性能工具——例如 UI 的 `Tree` 节点用轻量 `TreeItem` 对象承载上千行，而非完整 Node。
- **`RefCounted`**：向上一步，维护引用计数，归零自动删除，无需 `free()`，避免内存泄漏与悬垂指针。是**不需要存盘的纯逻辑系统、状态机、数据处理器的主力**。例：`FileAccess` 继承自 `RefCounted`，变量离开作用域时文件流自动关闭并释放。
- **`Resource`**：继承自 `RefCounted`，保留内存安全，额外支持序列化（`.tres` / `.res`）与 Inspector 显示，可用 `@export` 导出。它是代码与编辑器之间的桥梁——程序员只写一次蓝图，设计师便能纯靠 Inspector 创建、复制、微调数十个物品，无需碰 GDScript。

### 4.3 用 Resource 存数据（重构 cargo 系统）

**核心原则**：Resource 相对 Node 存数据的三大优势——**可序列化**（原生 `.tres` 存读）、**可共享**（多对象引用同一实例，降低开销）、**Inspector 集成**（可视化编辑与拖放）。

**反模式**：见 4.1 的 `CargoHold.gd`。

**正确做法**：

```gdscript
# ItemData.gd —— 单件物品蓝图
class_name ItemData extends Resource

@export var name: String = "Ship Item"
@export_multiline var description: String = ""
@export var icon: Texture2D
@export var stackable: bool = false
@export var trade_value: int = 10
```

```gdscript
# CargoData.gd —— 货舱本身也是 Resource，不是 Node
class_name CargoData extends Resource

@export var items: Array[ItemData] = []   # 类型化数组，保证只装合法物品

func add_item(new_item: ItemData):
    items.append(new_item)
    emit_changed()   # 内置：数据变更时广播，免去轮询

func remove_item(index: int):
    items.remove_at(index)
    emit_changed()
```

**UI 侧（Controller，MVC 中的 C）：数据运行时注入，而非导出**

```gdscript
# cargo_ui.gd
extends Control

var cargo_data: CargoData              # Model，运行时注入，不导出
@export var slot_scene: PackedScene    # View 用的单槽预制体

func initialize(new_cargo_data: CargoData) -> void:
    cargo_data = new_cargo_data
    cargo_data.changed.connect(update_ui)
    update_ui()

func update_ui() -> void:
    for child in $Grid.get_children():
        child.queue_free()
    for item in cargo_data.items:
        var slot = slot_scene.instantiate()
        $Grid.add_child(slot)
        if slot.has_method("set_icon"):
            slot.set_icon(item.icon)
```

**权衡与陷阱**：
- **MVC 分离**：Model（`CargoData`，知道物品数但完全不知道屏幕）／View（`GridContainer` 等，知道怎么画像素但不知道背包内容）／Controller（UI 脚本，中间人，监听 Model 信号并指挥 View）。严格分离可保证拖放 UI 的 bug 永远不会误删玩家的货物数据。
- **运行时注入而非导出**：生产中应在运行时动态注入易变的玩家数据，防止不同存档间"数据串味"，并支持动态加载背包。
- **收益**：场景膨胀大幅减少（1000 单位废料只是数据引用，几乎零性能成本）；可在无 UI 的情况下单元测试；存档直接 `ResourceSaver.save()`。

### 4.4 逻辑与表现分离

**核心原则**：若脚本既不需要进 Scene Tree，也不需要存盘，就应扩展 `RefCounted`（或 `Object`）。

**适用场景**：复杂计算、状态管理、工具函数。

**反模式**：为回合制战斗逻辑或掉落生成建一个通用 `Manager` 节点——`extends Node` 会继承大量引擎代码，纯粹数学或结构逻辑为此付出无谓代价。

**正确做法（静态工具函数）**：

```gdscript
class_name GameUtils extends RefCounted

const SCREEN_MARGIN: float = 50.0

static func get_screen_bounds(context_node: Node) -> Vector2:
    var world_size = context_node.get_viewport().get_visible_rect().size
    var camera = context_node.get_viewport().get_camera_2d()
    if camera:
        world_size = world_size / camera.zoom
    return Vector2(world_size.x / 2 + SCREEN_MARGIN, world_size.y / 2 + SCREEN_MARGIN)
```

**正确做法（有状态逻辑用实例化 RefCounted）**：

```gdscript
class_name DamageRoll extends RefCounted

var raw_damage: int
var armor_penetration: int

func _init(attacker_power: int, penetration: int) -> void:
    raw_damage = attacker_power
    armor_penetration = penetration

func calculate_against(target_armor: int) -> int:
    var effective_armor = max(0, target_armor - armor_penetration)
    return max(0, raw_damage - effective_armor / 2)
```

```gdscript
# PlayerShip.gd —— 用完即走，离开作用域自动释放
func attack(target: Node2D) -> void:
    var roll = DamageRoll.new(stats.weapon_power, stats.armor_pen)
    var damage = roll.calculate_against(target.stats.hull_armor)
    target.take_damage(damage)
```

RefCounted 也可持有长期状态，例如连击追踪器：

```gdscript
class_name ComboTracker extends RefCounted

var combo_count: int = 0
var last_hit_time: float = 0.0

func add_hit(time: float) -> void:
    combo_count = combo_count + 1 if time - last_hit_time < 1.0 else 1
    last_hit_time = time
```

Player 将 `ComboTracker.new()` 存为类级变量；Player 被销毁释放时引用消失，Godot 连带自动删除 `ComboTracker`，无需 `queue_free()`。

**权衡与陷阱**：
- 静态函数**无状态**，无法跨帧记忆。需要跟踪活跃数据（连击、复杂伤害）时，改用实例化 RefCounted。
- 显式写 `extends RefCounted`（即使省略 `extends` 时 GDScript 默认就是 RefCounted）——这是架构最佳实践，明确告知他人内存如何管理，无需读者记住引擎冷知识。
- 因从不调用 `add_child()`，这类对象永不进入视觉层级，引擎无需更新其 transform、检查暂停状态或发送树通知。

### 4.5 数据驱动模式：Strategy Pattern with Resources

**核心原则**：**Data-Driven Design** —— 游戏行为由资源（Resource）定义，而非硬编码脚本，让设计师无需程序员介入即可创造新敌人、物品、能力。

**适用场景**：需要频繁扩展行为变体的系统（AI 攻击、技能、掉落）。

**反模式**：写一个几千行、满是 `if/else` 的 `Enemy.gd` 枚举所有攻击类型。

**正确做法（抽象基类）**：

```gdscript
@abstract class_name AttackPattern extends Resource

@export var damage: int = 10
@export var cooldown: float = 1.0

@abstract func execute(user: Node2D, target: Node2D) -> void
```

`@abstract` 两大收益：**阻止实例化**（编辑器 New Resource 菜单只列出可用的子类如 `LaserAttack`，不再显示 `AttackPattern`）；**强制契约**（子类忘记实现 `execute()` 会立即报错，避免跑坏代码）。

```gdscript
# PlasmaBurst.gd —— 具体策略
extends AttackPattern

@export var fire_speed: float = 500.0
@export var projectile_scene: PackedScene

func execute(user: Node2D, target: Node2D) -> void:
    var plasma = projectile_scene.instantiate()
    plasma.position = user.position
    plasma.direction = (target.position - user.position).normalized()
    user.get_parent().add_child(plasma)
```

```gdscript
# EnemyDrone.gd —— 纯粹的 data-driven，不知道攻击"是什么"
class_name EnemyDrone extends CharacterBody2D

@export var attack_pattern: AttackPattern   # 设计师在 Inspector 拖入
@export var target: Node2D

func _on_attack_timer_timeout() -> void:
    if target:
        attack_pattern.execute(self, target)
```

**权衡与陷阱**：
- Drone 从不询问 `attack_pattern` 是激光、导弹还是近战，只调 `.execute()`——这就是**多态（polymorphism）**：共享同一接口的对象可被同等对待。
- 架构收益：`EnemyDrone` 对 feature-creep 免疫，可设计 50 种敌人行为而无需再打开该脚本。
- 制作"Plasma Bomber"变体只需：建通用 Drone 场景 → 用 `PlasmaBurstAttack.gd` 建 Resource 文件 → Inspector 调伤害/射速 → 拖入 Drone 的 Attack Pattern 槽位。**纯靠数据配置生成全新玩法内容。**

### 4.6 案例：用继承设计敌人系统

**核心原则**：为共享的根本身份建立基类，子类只写差异。

```gdscript
# BaseEnemy.gd —— 所有敌人的通用逻辑
class_name BaseEnemy extends Area2D

@export var speed: float = 200.0
@export var health: int = 50

func _physics_process(delta: float) -> void:
    global_position += Vector2.DOWN * speed * delta   # 默认：直线下落

func die() -> void:
    queue_free()
```

```gdscript
# KamikazeEnemy.gd —— 只声明独特之处 + 覆盖行为
class_name KamikazeEnemy extends BaseEnemy

@export var rotation_speed: float = 5.0   # 本类型特有的新变量

func _physics_process(delta: float) -> void:
    var player = get_tree().get_first_node_in_group("Player")
    if player:
        var direction = (player.global_position - global_position).normalized()
        var target_rotation = direction.angle() + PI / 2.0
        rotation = lerp_angle(rotation, target_rotation, rotation_speed * delta)
        global_position += Vector2.UP.rotated(rotation) * speed * delta
    else:
        global_position += Vector2.UP.rotated(rotation) * speed * delta

func _on_body_entered(body: Node2D) -> void:
    if body.is_in_group("Player") and body.has_method("take_damage"):
        body.take_damage(50)
    die()   # 调用从 BaseEnemy 继承的通用清理
```

**关键细节**：用 `lerp_angle` 手动计算角度而非 `look_at()`——`look_at()` 会瞬间对准目标，而手动插值让敌人平滑转向，给玩家闪避机会。`+ PI/2`（90°）是因为 Godot 中 0° 指向 X 轴右方，而飞船精灵的机头朝上。

**权衡与陷阱（继承的三大架构收益）**：
- **DRY**：日后想让敌人受伤闪红，只需在 `BaseEnemy.gd` 写一次，全部子类即时继承，无需改 20 个脚本。
- **可扩展性**：新建 `SniperEnemy`（逃跑）或 `TankEnemy`（护盾）只需写独特逻辑，基础已建好且经过测试。
- **系统信任（多态）**：所有敌人都 `extends BaseEnemy`，核心系统（如 EventBus）可盲目信任它们。导弹不需要知道自己击中 Kamikaze、Sniper 还是 Tank，只知道击中了保证带 `take_damage()` 的 `BaseEnemy`。

**组合技巧**：结合 Groups 与 Duck Typing（`has_method`），只对有效目标造成伤害：`if body.is_in_group("Player") and body.has_method("take_damage")`。

---

## 三章核心结论速查

| 场景 | 该用什么 | 原因 |
| --- | --- | --- |
| 固定结构 / 视觉组装 | Scene (`.tscn`) | 声明式、可视化、引擎优化 |
| 行为 / 逻辑 | Script (`.gd`) | 命令式、可复用、diff 干净 |
| 视觉变体（同身份） | Inherited Scene | 共享结构，只覆盖差异 |
| 逻辑变体 | Script 继承 | 共享函数/变量 |
| 功能追加（跨身份能力） | Resource 组件 | 可混搭，无继承链束缚 |
| 需要存盘的数据 | `Resource` (`.tres`) | 可序列化 + Inspector |
| 纯逻辑 / 临时计算 | `RefCounted` | 自动内存管理，无树开销 |
| 极致性能的临时结构 | `Object` | 最轻，但需手动 `free()` |
| 绘制 / 碰撞 / 空间层级 | `Node` | 唯一该用节点的场景 |
| 跨场景通信 | Signal（`Call Down, Signal Up`） | 解耦、可扩展、重构安全 |
| 同封装场景内的父子 | 直接引用 | 紧耦合是有意且安全的 |
| 节点逻辑集合管理 | Groups | 逻辑标签，与层级无关 |
| 复杂全局广播 | `EventBus` (Autoload) | 类型安全，IDE 可追踪 |
| 行为变体扩展 | Resource + Strategy Pattern | 数据驱动，无需写新代码 |

**贯穿三章的思路**：澄清（clarity）比极简更重要。每个场景都应有存在的理由，并尽可能独立运作；用信号或依赖注入进行通信；先原型找到乐趣，再在发现重复时抽取架构。
