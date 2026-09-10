# 数据驱动设计与游戏逻辑架构

> 本文档对应《Godot 4 Best Practices》第 11 章 *Adopting Data-Driven Design* 与第 12 章 *Structuring Gameplay Logic*。

---

## 第 11 章：数据驱动设计（Data-Driven Design）

### Data-Driven Design 与 Data-Oriented Design 的区别

**核心原则**
DDD 是**架构选择**（把逻辑与配置分离）；DOD 是**硬件级优化**（优化数据在内存中的布局以提高 CPU 缓存命中率）。两者名字相近但完全不同层次的问题。

**适用场景**
需要让策划/译者/Mod 作者在不改代码的前提下调整游戏内容时，用 DDD。需要极致性能（大量实体的内存遍历）时才考虑 DOD。

**反模式**
- 把 DDD 和 DOD 混为一谈，以为用 Resource 存数据就是"性能优化"。
- 在 GDScript 里手写 DOD 式 SoA 布局 —— GDScript 是高层自动内存管理语言，真正的 DOD 属于 Godot 的 C++ 底层 server。

**正确做法**
面向对象的传统写法把数据"焊死"在类型里：

```gdscript
# 反例：数据 (50, "Fire") 永久锁在类定义中
class_name FireSword extends Weapon
var damage: int = 50
var element: String = "Fire"
```

DDD 反转这个关系：写一个通用的 `Weapon` 空壳，把数据从外部喂进去：

```json
{ "weapon_id": "fire_sword", "damage": 50, "element": "Fire" }
```

**权衡与陷阱**
代码决定游戏**如何**运作（how，比如怎么挥剑），外部数据决定游戏**是什么**（what，比如多少伤害）。好处是新增内容不再增长代码库——JSON 里加 1000 把武器不需要写一行 GDScript。代价是数据与代码之间失去了编译期检查，必须靠验证兜底（见下方 Zero-Trust）。

---

### 逻辑与配置分离（Logic vs Configuration）

**核心原则**
代码是引擎（framework），配置是燃料（content）。程序写通用逻辑 `"当实体攻击时，造成 X 伤害、速度 Y"`，但不关心 X 和 Y 具体是多少。

**适用场景**
团队中同时有程序员和策划；或者单人项目进入"调数值"阶段——大部分开发时间其实花在反复试玩和微调上，而非写代码。

**反模式**
把数值硬编码进脚本，导致策划调一个 boss 攻速必须打开源码找变量、改完还要重启游戏验证。团队协作下这会造成：迭代变慢、误改代码引发语法错误、程序员与策划争抢同一个文件。

**正确做法**
- 程序员建立框架：通用逻辑不关心具体数值，只负责处理外部传入的数据。
- 策划填充内容：通过 JSON、CSV 表格，或 Inspector 中暴露的 custom resource 定义具体数值（哥布林 X=15 / Y=1.2，巨魔 X=40 / Y=0.5）。

**权衡与陷阱**
分离后形成异步流水线：程序员可以放心重构核心系统而不覆盖策划的平衡调整，策划可以随意试数值而不碰代码。代价是引入了数据来源这一层间接性，需要为数据格式做额外的约定与校验。

---

### 从硬编码重构为数据驱动 & 硬架构 / 软架构

**核心原则**
把游戏分为**硬架构**（底层通用系统，几乎不变，如 `move_and_slide`、渲染 server、输入处理）和**软架构**（游戏专属逻辑，如道具行为、背包）。DDD 中软架构**不应包含任何硬编码数值**，它只是一个等待外部数据注入的空壳。

**适用场景**
一开始就把软架构设计成"空壳"。如果已经写成了硬编码版本，按下面的方式重构。

**反模式**

```gdscript
# 反例：速度被永久锁在逻辑里
class_name BruiserEnemy extends CharacterBody2D

func _physics_process(delta: float) -> void:
    var speed: float = 150.0
    velocity = Vector2.RIGHT * speed
    move_and_slide()
```

即使把 `speed` 提到脚本顶部做常量，策划仍需翻阅 GDScript，非程序员改数值时有破坏代码的风险。

**正确做法**
用 `@export` 暴露一个自定义 Resource 槽位，把配置从代码中抽出：

```gdscript
# 数据驱动写法
class_name EnemyController extends CharacterBody2D

# @export 把这个空槽暴露到 Inspector
@export var stats: EnemyData

func _physics_process(delta: float) -> void:
    # 逻辑只读取被注入的数据
    velocity = Vector2.RIGHT * stats.speed
    move_and_slide()
```

**权衡与陷阱**
`@export` 是程序员与策划之间的桥梁：程序员写一次底层逻辑，策划在 Inspector 中拖拽不同的 `EnemyData` 文件即可改变敌人行为，完全不打开脚本编辑器。逻辑 `velocity = dir * speed` 与配置 `speed = 150.0` 的分界线画得越清晰，代码就越少需要改动。

---

### 用 Resource 管理数据：Prototype Pattern

**核心原则**
用**原型模式**：新建对象时复制/引用一个预先存在的"主模板"（prototype），而不是每次从零构建。Godot 中原型即 **Custom Resource**（`.tres` 文件），独立于 Scene Tree 存在。

**适用场景**
同一类实体大量存在（例如屏幕上 50 个 scout 敌人），且它们的静态属性共享、动态状态各自独立。

**反模式**
每个实例各自持有 `max_health`、`movement_speed`、`turn_rate`、`sprite_texture` —— 既浪费内存，又要同时更新 50 份数据。

**正确做法**
把对象拆成两半：**Prototype（数据）**存共享不变数据；**Instance（实体）**只存自身独有状态，并**持有对共享 prototype 的引用**。

```gdscript
# enemy_prototype.gd
class_name EnemyPrototype extends Resource

@export var prototype_id: String
@export var display_name: String
@export var base_health: int
@export var movement_speed: float
@export var sprite_texture: Texture2D
```

```gdscript
# enemy_instance.gd
class_name EnemyInstance extends CharacterBody2D

@export var stats: EnemyPrototype      # 注入原型数据
var current_health: int                # 只存本实例独有状态
@onready var sprite: Sprite2D = $Sprite2D

func _ready() -> void:
    current_health = stats.base_health
    sprite.texture = stats.sprite_texture

func take_damage(amount: int) -> void:
    # 扣的是 Instance 的血，不是 Prototype 的！
    current_health -= amount
    if current_health <= 0:
        queue_free()
```

**权衡与陷阱**
Resource 在内存中是**共享引用**。如果把 `Current Health` 这类会变的变量错误地放进共享的 `scout_prototype.tres`，射杀一个敌人会瞬间抽干屏幕上全部 50 个敌人的血。铁律：**静态数据放 Resource，当前状态放 Node**。

原型还可以**嵌套组合**，用更小的子原型拼装敌人，从而"压平节点层级、构建丰富的数据层级"：

```gdscript
@export var display_name: String
@export var base_health: int
@export var base_speed: float

# 混搭子原型
@export var movement_logic: MovementPrototype
@export var weapon_loadout: WeaponPrototype
```

Resource 也能承载逻辑——把它当作**无状态计算器**：接收当前物理状态，算出结果并返回。

```gdscript
# movement_prototype.gd
class_name MovementPrototype extends Resource

func calculate_velocity(current_pos: Vector2, target_pos: Vector2, speed: float) -> Vector2:
    return Vector2.ZERO   # 由具体子类覆写
```

```gdscript
# kamikaze_movement.gd —— 不存位置，只处理被交给它的数学
class_name KamikazeMovement extends MovementPrototype

func calculate_velocity(current_pos: Vector2, target_pos: Vector2, speed: float) -> Vector2:
    var direction: Vector2 = (target_pos - current_pos).normalized()
    return direction * speed
```

```gdscript
# enemy_instance.gd —— 在物理循环中直接调用嵌套逻辑
func _physics_process(delta: float) -> void:
    if stats.movement_logic != null:
        var new_velocity = stats.movement_logic.calculate_velocity(
            global_position, player.global_position, stats.base_speed
        )
        velocity = new_velocity
        move_and_slide()
```

---

### 用 JSON 外置数据（Externalizing with JSON）

**核心原则**
`.tres` 仍紧绑 Godot 编辑器。要让外部人员（外包关卡设计师、译者）参与，需改用**通用数据格式**。纯文本中 JSON 是事实标准——它轻量，且结构与 Godot `Dictionary` 的键值对完全对应。

**适用场景**
需要非程序员用自己熟悉的工具（记事本、Excel）编辑配置；需要本地化文本；需要支持热重载。

**反模式**
二进制格式虽然更小更快，但人类难以调试、校验和编辑；在编辑器外部场景尤其不适用。

**正确做法**

```json
{
  "level_name": "Asteroid Belt",
  "base_difficulty": 1.5,
  "waves": [
    { "enemy_id": "scout", "count": 5, "delay": 1.0 },
    { "enemy_id": "bruiser", "count": 2, "delay": 2.5 }
  ]
}
```

JSON 在编译产物之外，失去了 GDScript 的安全网，必须采用 **Zero-Trust 策略**：*Never trust, always verify*。假设外部文件是坏的、损坏的、或试图搞崩你的游戏。三大风险：人为笔误（`"health": "one hundred"`）、结构损坏（删掉一个逗号或整个 `waves` 数组）、恶意构造（超大数字或异常结构）。

```gdscript
class_name LevelLoader extends Node

func load_level_data(file_path: String) -> Dictionary:
    # 1. 文件是否存在
    if not FileAccess.file_exists(file_path):
        push_error("Level file not found: ", file_path)
        return {}

    # 2. 打开并读取纯文本
    var file: FileAccess = FileAccess.open(file_path, FileAccess.READ)
    var json_text: String = file.get_as_text()

    # 3. 解析 JSON
    var json: JSON = JSON.new()
    var error: Error = json.parse(json_text)
    if error != OK:
        push_error("JSON Parse Error at line ", json.get_error_line(), ": ",
                   json.get_error_message())
        return {}

    # 4. 根结构类型检查
    var data = json.get_data()
    if typeof(data) != TYPE_DICTIONARY:
        push_error("Invalid JSON format: Expected a base object/dictionary.")
        return {}

    # 5. 键与值类型校验（Zero-Trust）
    if not data.has("waves") or typeof(data["waves"]) != TYPE_ARRAY:
        push_error("Level data is missing a valid 'waves' array.")
        return {}

    return data
```

这条流水线依次通过：存在性检查 → 可读性检查 → 语法检查 → 根结构检查 → 键检查 → 类型检查。数据走到尽头时已在数学上证明它是安全的，可以放心注入游戏。

**权衡与陷阱**
写校验代码起初显得繁琐，但这是专业开发者的标志：游戏不会因为 Mod 作者笔误而崩溃到桌面，而是忽略损坏文件、在控制台打印友好警告并优雅地继续运行。

**热重载**：JSON 是动态读取的，可以绑定热键（如 F5）触发 `load_level_data()`。工作流变成：游戏运行中改 `level_1.json` 的 `count` → 保存 → 切回按 F5 → 立即生效。把"平衡游戏"从繁琐杂务变成流畅体验。

---

### 可 Mod 系统设计（Moddable Systems）

**核心原则**
DDD 的终极形态是把系统开放给社区。因为逻辑（硬架构）与配置（软架构）已分离，内容生产不必只由自己承担。

**适用场景**
想延长游戏生命周期、借助玩家社区持续产出内容时。

**反模式**
只从 `.pck`（导出时的封包归档，默认是开放归档，导出设置中可选加密）读取数据。这是封闭系统，普通玩家无法打开或修改其中的数据。

**正确做法**
让游戏在启动时扫描 `user://mods/` 目录。`user://` 指向玩家操作系统上可写的真实目录（如 Windows 的 AppData），能发现并加载玩家新建的 JSON。

加载外部资源（Mod 作者自定义美术）时同样零信任：

```gdscript
func load_external_texture(path: String) -> ImageTexture:
    # 1. 校验：文件确实存在
    if not FileAccess.file_exists(path):
        push_warning("Mod asset missing: ", path)
        return null

    # 2. 加载原始数据
    var image: Image = Image.new()
    var error: Error = image.load(path)
    if error != OK:
        push_warning("Failed to load mod image: ", path)
        return null

    # 3. 转换为引擎可用的 Texture2D
    return ImageTexture.create_from_image(image)
```

三步：`FileAccess` 校验存在性 → `Image.new()` + `load()` 读取原始像素并检查错误码 → `ImageTexture.create_from_image()` 转成渲染节点能用的纹理（原始 Image 不能直接赋给 `Sprite2D`）。

---

### Mod 加载管线（The Mod Loading Pipeline）

**核心原则**
把原型、JSON 解析、Zero-Trust 校验、外部资源加载串成一条完整管线。

**适用场景**
玩家把 `dreadnought.json` 和 `dreadnought.png` 放进 `user://mods/`，游戏启动时自动接入。

**正确做法（五个步骤）**
1. **Discovery**：扫描 `user://mods/` 发现新文件。
2. **Parsing and validation**：读取 JSON，走严格 Zero-Trust 流水线。
3. **Texture loading**：调用 `load_external_texture()` 把自定义 PNG 载入内存。
4. **Dynamic prototype creation**：纯代码创建全新的 `EnemyPrototype` Resource，用 JSON 数值和新纹理填充。
5. **Injection**：把新原型推入中央 Autoload，供全局查找。

因为 Custom Resource 就是对象，可以直接用 `.new()` 在内存中实例化：

```gdscript
# 假设 JSON 已解析、PNG 纹理已加载
func create_and_inject_mod(mod_id: String, parsed_json: Dictionary,
                           custom_texture: Texture2D) -> void:
    # STEP 4：动态创建原型
    var new_prototype: EnemyPrototype = EnemyPrototype.new()
    new_prototype.display_name = parsed_json["display_name"]
    new_prototype.base_health = parsed_json["base_health"]
    new_prototype.base_speed = parsed_json["speed"]
    new_prototype.sprite_texture = custom_texture

    # STEP 5：注入全局 Autoload 数据库
    if not EnemyDatabase.has_enemy(mod_id):
        EnemyDatabase.register_enemy(mod_id, new_prototype)
```

**权衡与陷阱**
把新 Resource 存进中央 `EnemyDatabase` Autoload 后，其余游戏逻辑无需知道某个敌人是内置的还是 Mod 加载的。Wave Spawner 随机选中 `dreadnought` ID 时查询数据库即可——`EnemyInstance` 只是读取注入的原型并让飞船飞过屏幕，而这个敌人在你编译代码时根本不存在。

---

## 第 12 章：结构化游戏逻辑（Structuring Gameplay Logic）

### 架构路线图与 Separation of Concerns

**核心原则**
按**关注点分离**把程序切成互相隔离的部分。一个 concern 就是一个具体职责（算物理、播音频、更新 UI、存档）。不要写一个巨大的 `player.gd` 同时管理所有事情。

**适用场景**
项目从原型走向商业级代码库时；团队规模扩大时。

**反模式**
把用户输入、物理计算、UI 更新紧耦合进单个文件以最快跑通原型。短期有效，但随着项目扩张，"用纠缠的一次性方案解决复杂问题"，最终离奇地改主菜单会搞坏敌人生成逻辑。

**正确做法**
三层职责划分：
- **Presentation Layer**：只负责渲染视觉、管理动画、播放音频，是游戏在 Scene Tree 中的物理呈现。
- **Domain Layer**：纯数学与系统核心，规则、状态机、机制在此独立于视觉引擎存在。
- **Persistence Layer**：负责存档/读档的安全数据结构，不干扰进行中的游戏。

**权衡与陷阱**
把它想象成瀑布：纯数据存在最上层，中间翻译成数学规则，按需向下流动，在最底层实际驱动画面。隔离职责后代码可读、可测、可无限扩展。

---

### 识别 God Class（上帝类）

**核心原则**
God class 是一个试图管理游戏所有方面的孤立脚本，是项目可伸缩性最大的敌人。它通常源于善意，被"快速开发"的承诺诱惑而不断堆叠任务。

**适用场景**
诊断阶段——重构前的第一步是精准定位结构腐坏的起点。

**反模式诊断清单**（命中多项就该重构）
- **超出可控规模**：单个脚本长达数百甚至数千行，几乎必然承担了过多职责。
- **同时管理多个领域**：在同一脚本里直接计算敌人伤害（gameplay logic）、更新玩家血条（UI）、把新高分写入硬盘（persistence）。真正的 God class 拒绝委派。
- **持有大量节点引用**：脚本顶部堆着十几个指向 Scene Tree 中毫不相关节点的 `@onready var`，像一片墓碑。
- **充当万能枢纽**：路由项目里所有信号，或用 Autoload 存全局状态，迫使从主菜单到背景陨石的每个对象都直接依赖它。

**权衡与陷阱（隐藏成本）**
- **改动的爆炸半径**：代码纠缠导致调整玩家速度可能弄坏敌人 AI，改一处像拆炸弹。
- **调试噩梦**：在庞大纠缠的脚本里定位原因是"大海捞针"。
- **团队瓶颈**：所有程序员被迫编辑同一文件，像共同握一个方向盘，保证每天合并冲突，新人几乎无法上手。

---

### 分离表现与逻辑（Presentation vs Domain）

**核心原则**
视觉表现应当对底层数学规则**完全无知**。游戏中"在做什么"（逻辑）必须与"看起来怎样"（表现）解耦。

**适用场景**
任何时候都适用。Godot 中特别诱人的做法是让 Scene Tree 主导游戏逻辑——检查激光 Sprite 的 `global_position` 判断是否飞出屏幕，或用挂在敌人上的 `Timer` 节点跟踪攻击冷却。

**反模式**

```gdscript
# 反例：表现层与领域层危险地纠缠
# hud.gd
extends CanvasLayer

var current_score: int = 0
@onready var score_label = $ScoreLabel

func _on_enemy_defeated(base_points: int, combo_multiplier: float) -> void:
    # 错误：UI 脚本在做 gameplay 数学！
    current_score += (base_points * combo_multiplier)
    score_label.text = "Score: " + str(current_score)
```

如果玩家血量被直接存在 `ProgressBar` 的 `value` 里，策划把血条换成文本 `Label` 时，游戏立刻因空引用崩溃——纯外观改动弄坏了核心机制。

**正确做法**
Presentation Layer 的**黄金法则**是保持"哑"：只做人机之间的双向翻译器。玩家按键时它盲目把输入往下传；逻辑更新分数时它只把数字画到屏幕。引入第三个脚本作为数学与视觉之间的胶水：

```gdscript
# 1. score_manager.gd（Domain Layer —— 无视觉）
extends Node

var current_score: int = 0
signal score_changed(new_score: int)

func add_points(base_points: int, combo_multiplier: float) -> void:
    current_score += (base_points * combo_multiplier)
    score_changed.emit(current_score)
```

```gdscript
# 2. hud.gd（Presentation Layer —— 无数学）
extends CanvasLayer
@onready var score_label = $ScoreLabel

func update_score_display(new_score: int) -> void:
    score_label.text = "Score: " + str(new_score)
```

```gdscript
# 3. gameplay_context.gd（胶水 —— 把两者接起来）
extends Node

@export var score_manager: Node
@export var hud: CanvasLayer

func _ready() -> void:
    # Context 安全地把 Domain 的输出接到 Presentation 的输入
    score_manager.score_changed.connect(hud.update_score_display)
```

**权衡与陷阱**
Domain Layer 对 Scene Tree 完全失明——不知道 `Sprite2D`、`Tween`、`AudioStreamPlayer` 的存在，只处理原始数据（活跃敌人数组、船体完整度整数、AI 状态机）。收益是可测试性与可预测性：领域逻辑不依赖渲染循环或物理帧，不会被图形卡顿或缺失资源弄坏，可以在不加载关卡、不点鼠标的情况下自动验证激光伤害计算是否正确。

此处沿用 **Call Down, Signal Up**：父节点（controller）直接调用子节点方法更新表现；子节点（视觉节点）只向上发信号通知"动画结束"或"发生输入"，**子节点永远不知道父节点是谁**。

---

### Pure Data Object、Context 与 Persistence

**核心原则**
把长期状态数据与功能逻辑分离，用 **Pure Data Object** 承载状态。通过继承 `RefCounted` 或 `Resource`（而非 `Node`），使这些脚本完全脱离 Scene Tree，成为只有变量、没有功能代码的简单 struct。

**适用场景**
需要存储游戏状态时。最坏的习惯是把关键数据存在 Scene Tree 节点里——例如把分数存在 `Label` 节点、或用全局 `Node` Autoload 持有所有变量。

**反模式**
把纯数据塞进全局 Autoload 让所有脚本随意访问。给主菜单全局访问"对局中玩家血量"的权限是灾难配方：任何脚本能访问，就意味着任何脚本都能意外破坏它。

**正确做法**

```gdscript
class_name LevelState extends RefCounted

var current_score: int = 0
var current_wave: int = 1
var player_health: int = 100
var is_game_over: bool = false
```

零逻辑、无函数、无信号、无数学——纯粹的被动容器。活跃 gameplay 脚本可以安全地修改这个状态，不必担心物理帧、暂停或 `queue_free()` 生命周期 bug。复杂类型（如昼夜状态的枚举）也安全：存时转成整数，读时通过枚举的 `.values()` 数组安全转回。

**Context 分层架构**
上一章我们构建了全局 Service（如 `AudioService`），但 gameplay 逻辑与状态管理**不能用全局访问**。把游戏划分为若干 **Context**：一个 Context 代表游戏的一个主要状态，拥有安全边界与独立规则。它们挂在 `RootContext`（主场景）之下，`RootContext` 管理全局系统，其下可有 `MainMenuContext` 与 `GameplayContext`。`GameplayContext` 严格负责构建和管理关卡、wave controller 与 UI，并安全持有该场对局的 Pure Data Object，确保外部脚本无法篡改。

**Persistence Layer**
`GameplayContext` 从 Scene Tree 卸载的瞬间，它持有的安全数据也随之消失。Persistence Layer 负责需要跨会话存活的数据。因为状态已隔离成纯数据对象并有了严格的 Context 层级，存档变得简单：不需要在 Scene Tree 里搜寻玩家血量，也不需要保存脆弱的节点路径（重排项目就会失效），只要向 `GameplayContext` 要它的数据对象，交给 Persistence Layer 即可。

**完整数据管线**（从屏幕上的操作一直到硬盘）
1. **Gameplay**：玩家在世界中执行操作（击败 boss 获得新激光武器）。
2. **LevelState**：活跃节点层级登记该事件并更新临时局部状态（玩家背包数组）。
3. **GameplayContext**：遵循 signal up，`LevelState` 发出携带更新后背包的信号，`GameplayContext` 接住并为当前关卡安全持有。
4. **Persistence Manager**：存档触发时（手动或场景切换），`GameplayContext` 把纯数据交给专门的文件管理系统。
5. **JSON file**：Persistence Manager 转换数据并安全写入物理磁盘上的 `.json`。

file manager 正是全局 Service 的完美候选——它只提供读写工具：

```gdscript
extends Node
# PersistenceManager.gd

# 用于警告 Contexts 场景切换即将发生
signal pre_save_path_changed

const BASE_SAVE_DIR: String = "user://game_saves/"
const MASTER_FILE_NAME: String = "void_defenders_save.json"

func _ready() -> void:
    # DirAccess 让我们安全地与 OS 文件系统交互
    if not DirAccess.dir_exists_absolute(BASE_SAVE_DIR):
        # 父目录缺失时一并递归创建
        DirAccess.make_dir_recursive_absolute(BASE_SAVE_DIR)

func write_save_data(save_dict: Dictionary) -> void:
    var file_path: String = BASE_SAVE_DIR + MASTER_FILE_NAME
    var file = FileAccess.open(file_path, FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(save_dict))
        file.close()
```

用 `DirAccess.dir_exists_absolute()` 显式检查目录，保证全新安装时写文件不会崩溃。用 `pre_save_path_changed` 信号当警铃：玩家退回主菜单时发出，提醒 `GameplayContext` 在当前关卡卸载前打包并序列化其纯数据对象，保证零数据丢失。

```gdscript
class_name GameplayContext extends Node
# GameplayContext.gd

var level_state: LevelState

func _ready() -> void:
    level_state = LevelState.new()
    PersistenceManager.pre_save_path_changed.connect(_on_pre_save_path_changed)

func _on_pre_save_path_changed() -> void:
    # 玩家退出前自动触发
    var save_dict: Dictionary = {
        "score": level_state.current_score,
        "wave": level_state.current_wave,
        "health": level_state.player_health
    }
    PersistenceManager.write_save_data(save_dict)
```

**权衡与陷阱**
**不是每个 Godot 项目都需要这些严格分层。** 周末 game jam、简单手机解谜、小型原型里，用 `@onready` 把机制直接耦合进 Scene Tree 完全可以接受，因为项目永远不会大到出现结构腐坏。但商业作品、数据密集的 RPG、或需要团队维护多年的代码库，这套架构是**强制性的**——前期多花的时间是一份保险，确保代码库随规模扩张仍保持灵活、可测、健壮。

---

### 重构单体脚本（Refactoring a Monolithic Script）

**核心原则**
不是把大脚本随意剁成更小但同样纠缠的碎片，而是按**职责**画出严格的架构边界。反例原型：

```gdscript
class_name LevelManager extends Node
# 反例：单体 God Class

# 1. 表现层：紧耦合到具体的 Scene Tree UI 节点
@onready var score_label = $HUD/MarginContainer/ScoreLabel
@onready var wave_label = $HUD/MarginContainer/WaveLabel
@onready var game_over_screen = $HUD/GameOverScreen
@onready var explosion_audio = $ExplosionPlayer

# 2. 纯数据：状态变量被困在功能性 Node 里
var current_score = 0
var current_wave = 1
var player_health = 100
var is_game_over = false

func _ready():
    # 3. 全局依赖：靠 Autoload 完成所有通信
    Events.enemy_died.connect(_on_enemy_died)
    Events.player_hit.connect(_on_player_hit)
    update_ui()

func _on_enemy_died(point_value):
    if is_game_over:
        return
    current_score += point_value                      # 领域逻辑
    if current_score > current_wave * 1000:
        current_wave += 1
    explosion_audio.play()                            # 表现层
    update_ui()

func _on_player_hit(amount):
    player_health -= amount                           # 领域逻辑
    if player_health <= 0:
        is_game_over = true
        game_over_screen.visible = true               # 表现层
        Events.play_music.emit("game_over_theme")     # 全局通信

func update_ui():
    score_label.text = "SCORE: %d" % current_score
    wave_label.text = "WAVE: %d" % current_wave
```

**反模式（问题剖析）**
- **没有边界**：`_on_enemy_died()` 里先做数学（领域），紧接着整个脚本切换身份去播音频、渲染 UI（表现）。如果策划从场景删掉 `ExplosionPlayer` 节点，`explosion_audio.play()` 会抛致命空引用；Godot 遇错即停止执行函数，脚本会在到达 `update_ui()` 前崩掉——**仅仅因为少了一个音效，屏幕上的分数就不再更新**。
- **数据被困**：`current_score`、`player_health` 锁在这个物理 Node 里，存档系统必须去活跃 Scene Tree 里搜寻这个特定节点。
- **依赖全局魔法**：它监听 `Events` Autoload，意味着**另一个关卡的敌人死亡、甚至测试场景里的敌人死亡**都可能意外让这里的分数上涨。

**正确做法（五步重构）**

**第 0 步：先强制静态类型。** 把大脚本拆开、把函数移进不同文件时，很容易在新建的各层之间传错数据；无类型代码会被 Godot 盲目接受，直到运行时才崩溃。先启用 Static Typing，编辑器会立刻用红行标出错误的接线。

```gdscript
# 反例：无类型、含糊
var score = 0
func add_points(amount):
    score += amount

# 正确：静态类型
var score: int = 0
func add_points(amount: int) -> void:
    score += amount
```

**第 1 步：抽出 Game State（Pure Data Layer）。** 注意继承 `RefCounted`，不挂在编辑器里任何对象上：

```gdscript
class_name LevelState extends RefCounted

var current_score: int = 0
var current_wave: int = 1
var player_health: int = 100
var is_game_over: bool = false
```

**第 2 步：创建 Controller（Domain Logic Layer）。** 它制定关卡规则、修改状态，但不碰任何视觉，严格依赖注入给它的 `LevelState`：

```gdscript
class_name LevelController extends Node

signal score_changed(new_score: int)
signal game_over

var state: LevelState

func _init(initial_state: LevelState) -> void:
    state = initial_state

func enemy_destroyed(point_value: int) -> void:
    if state.is_game_over:
        return
    state.current_score += point_value
    score_changed.emit(state.current_score)

func player_took_damage(amount: int) -> void:
    state.player_health -= amount
    if state.player_health <= 0:
        state.is_game_over = true
        game_over.emit()
```

`LevelController` 是领域层的活跃大脑：初始化时通过 **Dependency Injection** 接收 `LevelState`，在关键事件（敌人死亡、玩家受伤）时安全修改其变量。它**绝不直接触碰 Scene Tree 或 UI**，只做底层计算并向上广播信号（`score_changed`、`game_over`），让表现层独立监听并更新图形。

**第 3 步：创建 Renderer（Presentation Layer）。** HUD 主动不去监听信号、不监控游戏状态，而是纯被动的 helper。遵循 call down，由 `GameplayContext` 直接调用 HUD 的函数并交付最终数据：

```gdscript
class_name HUDManager extends CanvasLayer

@onready var score_label: Label = $MarginContainer/ScoreLabel
@onready var game_over_screen: Control = $GameOverScreen

func update_score_display(new_score: int) -> void:
    score_label.text = "SCORE: %d" % new_score

func show_game_over() -> void:
    game_over_screen.visible = true
```

三个关键改进：**无游戏数学**（接收预算好的整数，不关心敌人值多少分或连击倍率）；**无状态检查**（`show_game_over()` 不检查血量是否归零，盲目信任领域层，被命令时才显示）；**无全局依赖**（完全没有 `Events.enemy_died.connect` 这类连接）。

**第 4 步：通过 Dependency Injection 绑定 Service。** 在 `GameplayContext`（管理关卡的安全父节点）中编排这一切，而不是靠纠缠的 Autoload 网络去找玩家分数：

```gdscript
class_name GameplayContext extends Node

@onready var hud_manager: HUDManager = $HUDManager
var level_controller: LevelController
var level_state: LevelState

func _ready() -> void:
    # 1. 初始化纯数据状态（从 Persistence 加载）
    var saved_data: Dictionary = PersistenceManager.read_save_data()
    level_state = LevelState.new()
    if not saved_data.is_empty():
        level_state.current_score = saved_data.get("score", 0)
        level_state.current_wave = saved_data.get("wave", 1)
        level_state.player_health = saved_data.get("health", 100)

    # 2. 把状态注入领域逻辑
    level_controller = LevelController.new(level_state)
    add_child(level_controller)

    # 3. 把逻辑连到表现（call down, signal up）
    level_controller.score_changed.connect(hud_manager.update_score_display)
    level_controller.game_over.connect(hud_manager.show_game_over)
```

**权衡与陷阱（重构前后对比）**

| 维度 | 问题（God class） | 方案（分层架构） |
|---|---|---|
| 职责 | 单个脚本同时算数学、更新 UI 文本、触发音频 | 完全分离为表现节点与纯数学的领域 controller |
| 数据存储 | `current_score` 等变量永久困在逻辑脚本中 | 状态隔离进 Pure Data Object（`LevelState`），易于序列化 |
| 数据流 | 脚本靠全局 Autoload 通信，隐藏依赖 | 父 Context 用 Dependency Injection 只把数据交给需要的脚本 |
| 可测试性 | 测试需启动整个 Scene Tree、UI 与图形引擎 | Controller 可通过传入假数据在无头环境下完全隔离测试 |
| 文件组织 | 按类型随意堆放（全丢进 `/Scripts`） | 按功能智能分组（如 `/Features/LevelManagement/`） |

现在可以给 `LevelController` 传一个假的 `LevelState` 写自动化测试，完全不需要加载 `HUDManager` 或启动图形引擎。策划改 UI，数学存活；程序员改计分公式，视觉完好——这就是 Separation of Concerns 的终极威力。
