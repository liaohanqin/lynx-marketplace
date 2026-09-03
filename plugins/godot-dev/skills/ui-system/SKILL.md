---
name: ui-system
description: >
  UI 系统。生成游戏 UI 组件（HUD、菜单、对话框等），支持分层架构和响应式布局。
  当用户要求「UI / 界面 / 菜单 / HUD / 对话框 / 血条 / 按钮」时激活。
---

# UI 系统

生成游戏 UI 组件和界面。

## UI 分层架构

```
UI (CanvasLayer)
├── HUD (Control) - 游戏中始终显示
│   ├── HealthBar / ManaBar / Minimap / QuickSlots
├── Menus (Control) - 菜单层
│   ├── MainMenu / PauseMenu / SettingsMenu
├── Popups (Control) - 弹窗层
│   ├── ConfirmDialog / ItemPopup
└── Overlay (Control) - 最上层
    ├── LoadingScreen / FadeTransition / Notifications
```

## 布局与锚点

Godot 4 的 Control 布局核心是 **anchor（锚点）+ offset（偏移）**：

- 全屏铺满：四个 anchor 设为 0..1（`set_anchors_preset(Control.PRESET_FULL_RECT)`）
- 居中元素：`PRESET_CENTER`
- 顶部栏：`PRESET_TOP_WIDE`
- 底部栏：`PRESET_BOTTOM_WIDE`

响应式布局应优先用容器节点而非手动坐标：

| 容器 | 用途 |
|------|------|
| VBoxContainer | 垂直排列 |
| HBoxContainer | 水平排列 |
| GridContainer | 网格排列 |
| MarginContainer | 加边距 |
| CenterContainer | 居中子节点 |
| PanelContainer | 带背景面板 |

## 信号与事件

UI 按钮通过 `pressed` 信号响应：

```gdscript
@onready var play_button: Button = $VBox/PlayButton

func _ready() -> void:
    play_button.pressed.connect(_on_play_pressed)

func _on_play_pressed() -> void:
    get_tree().change_scene_to_file("res://scenes/game.tscn")
```

## UI 控制器模板

```gdscript
class_name {{CLASS_NAME}}
extends Control

signal opened
signal closed

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

## 常见 UI 组件

### 血条（进度条绑定属性）

用 `ProgressBar` 或 `TextureProgressBar`，绑定到实体的 `health_changed` 信号：

```gdscript
func _on_health_changed(old: int, new: int) -> void:
    health_bar.value = new
    health_bar.max_value = player.max_health
```

### 弹窗确认框

用 `ConfirmationDialog` 节点，`confirmed` 信号处理确定。

### 场景切换

```gdscript
# 切场景（带淡入淡出可用 AnimationPlayer 叠加）
get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
```

## 使用示例

```
做一个主菜单：有「开始游戏」「设置」「退出」三个按钮，开始游戏切换到主场景。
```
