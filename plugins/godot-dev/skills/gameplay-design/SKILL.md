---
name: gameplay-design
description: >
  玩法内容策划。生成核心循环、战斗系统、成长系统等玩法设计文档，并提供 GDScript 代码模板。
  当用户要求「玩法设计 / 核心玩法 / 战斗系统 / 成长系统 / 数值设计 / 关卡设计」时激活。
---

# 玩法内容策划

生成玩法设计文档和配套代码。

## 输出模板

```markdown
# {游戏名称} - 玩法设计

## 1. 核心循环

挑战 → 行动 → 反馈 → 奖励 → 成长 → 更大挑战

- 微循环 (秒): 攻击→命中→击杀
- 短循环 (分钟): 清怪→拿装备→前进
- 中循环 (10分钟): 通关→结算→下一关
- 长循环 (小时): 解锁→尝试→挑战更高

## 2. 战斗系统
## 3. 成长系统
## 4. 目标系统
```

## 战斗系统设计要点

| 攻击类型 | 消耗 | 伤害 | 特点 |
|----------|------|------|------|
| 普攻 | 无 | 100% | 主要输出 |
| 蓄力 | 时间 | 200% | 有硬直 |
| 技能 | MP | 150%+ | 特殊效果 |

防御方式：闪避（无敌帧）、格挡（减伤）、弹反（反弹+眩晕）。

## 成长系统设计要点

经验公式示例：`升级经验 = 100 × 等级²`

装备品质分层：白(无词条) → 绿(1词条) → 蓝(2词条) → 紫(3词条+套装) → 橙(4词条+特效)。

## 代码模板

### 战斗管理器

```gdscript
class_name CombatManager
extends Node

signal damage_dealt(attacker, target, damage)

const HIT_STOP := 0.05

func deal_damage(atk: Node, def: Node, base: float, multiplier := 1.0) -> int:
    var atk_power = atk.get_stat("atk") if atk.has_method("get_stat") else 0
    var def_power = def.get_stat("def") if def.has_method("get_stat") else 0
    # 伤害公式: 攻击 × 倍率 × (100 / (100 + 防御))
    var damage = base * multiplier * (1 + atk_power / 100.0)
    damage *= 100.0 / (100.0 + def_power)
    var final = int(max(1, damage))
    if def.has_method("take_damage"):
        def.take_damage(final)
    damage_dealt.emit(atk, def, final)
    _hit_stop()
    return final

func _hit_stop() -> void:
    Engine.time_scale = 0.0
    await get_tree().create_timer(HIT_STOP, true, false, true).timeout
    Engine.time_scale = 1.0
```

### 属性组件

```gdscript
class_name StatsComponent
extends Node

signal level_up(new_level)

@export var base_hp := 100
@export var base_atk := 10
@export var hp_growth := 10.0
@export var atk_growth := 2.0

var level := 1
var exp := 0
var bonuses: Dictionary = {}

func get_stat(stat: String) -> float:
    var base = get("base_" + stat) or 0
    var growth = get(stat + "_growth") or 0
    var bonus = bonuses.get(stat, 0.0)
    return (base + level * growth) * (1 + bonus)

func add_exp(amount: int) -> void:
    exp += amount
    while exp >= _exp_required():
        exp -= _exp_required()
        level += 1
        level_up.emit(level)

func _exp_required() -> int:
    return 100 * level * level
```

## 设计原则

1. 数值用公式而非硬编码，便于调平衡。
2. 核心循环要短（秒级反馈），奖励要及时。
3. 伤害公式要避免防御堆到免疫（用 `100/(100+防御)` 这类递减公式）。
4. 策划案落盘到 `docs/planning/`，代码落盘到 `scripts/`。
