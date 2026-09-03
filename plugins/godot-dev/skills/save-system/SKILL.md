---
name: save-system
description: >
  存档系统。管理游戏进度的保存和加载，支持多存档槽、自动保存、加密存档。
  当用户要求「存档 / 保存 / 加载 / Save / Load / 进度」时激活。
---

# 存档系统

管理游戏进度的保存和加载。

## 存档目录结构

```
user://
└── saves/
    ├── settings.cfg        # 全局设置
    ├── slot_1/
    │   ├── save.json       # 主存档数据
    │   ├── screenshot.png  # 存档截图
    │   └── meta.json       # 元数据
    ├── slot_2/  slot_3/
    └── autosave/
```

## 存档管理器（Autoload）

```gdscript
class_name SaveManager
extends Node

signal save_completed(slot: int)
signal load_completed(slot: int)
signal save_failed(slot: int, error: String)
signal load_failed(slot: int, error: String)

const SAVE_DIR = "user://saves/"
const MAX_SLOTS = 3
const AUTOSAVE_SLOT = -1
const SAVE_VERSION = "1.0.0"

@export var autosave_enabled: bool = true
@export var autosave_interval: float = 300.0
@export var encrypt_saves: bool = false
@export var encryption_password: String = "your_secret_key"

var current_slot: int = -1
var game_data: Dictionary = {}
var _is_saving: bool = false
var _is_loading: bool = false

func _ready() -> void:
    _ensure_save_directory()

func _ensure_save_directory() -> void:
    var dir = DirAccess.open("user://")
    if not dir.dir_exists("saves"):
        dir.make_dir("saves")
    for i in range(MAX_SLOTS):
        if not dir.dir_exists("saves/slot_%d" % (i + 1)):
            dir.make_dir("saves/slot_%d" % (i + 1))
    if not dir.dir_exists("saves/autosave"):
        dir.make_dir("saves/autosave")

func save_game(slot: int) -> bool:
    if _is_saving:
        return false
    _is_saving = true
    var slot_path = _get_slot_path(slot)
    var save_data = _collect_save_data()
    save_data["_meta"] = {
        "version": SAVE_VERSION,
        "timestamp": Time.get_unix_time_from_system(),
        "datetime": Time.get_datetime_string_from_system(),
    }
    var success = _write_save_file(slot_path + "/save.json", save_data)
    if success:
        current_slot = slot
        save_completed.emit(slot)
    else:
        save_failed.emit(slot, "Failed to write save file")
    _is_saving = false
    return success

func _collect_save_data() -> Dictionary:
    var data = {}
    data["game_data"] = game_data.duplicate(true)
    get_tree().call_group("saveable", "on_save", data)
    return data

func load_game(slot: int) -> bool:
    if _is_loading:
        return false
    _is_loading = true
    var slot_path = _get_slot_path(slot)
    var save_data = _read_save_file(slot_path + "/save.json")
    if save_data.is_empty():
        load_failed.emit(slot, "Save file not found or corrupted")
        _is_loading = false
        return false
    var save_version = save_data.get("_meta", {}).get("version", "0.0.0")
    if not _is_version_compatible(save_version):
        load_failed.emit(slot, "Incompatible save version: " + save_version)
        _is_loading = false
        return false
    game_data = save_data.get("game_data", {})
    get_tree().call_group("saveable", "on_load", save_data)
    current_slot = slot
    load_completed.emit(slot)
    _is_loading = false
    return true

func _write_save_file(path: String, data: Dictionary) -> bool:
    var json_string = JSON.stringify(data, "\t")
    if encrypt_saves:
        json_string = _encrypt(json_string)
    var file = FileAccess.open(path, FileAccess.WRITE)
    if file:
        file.store_string(json_string)
        file.close()
        return true
    return false

func _read_save_file(path: String) -> Dictionary:
    if not FileAccess.file_exists(path):
        return {}
    var file = FileAccess.open(path, FileAccess.READ)
    if not file:
        return {}
    var content = file.get_as_text()
    file.close()
    if encrypt_saves:
        content = _decrypt(content)
    var json = JSON.new()
    if json.parse(content) != OK:
        push_error("JSON parse error: " + json.get_error_message())
        return {}
    return json.data

func _is_version_compatible(save_version: String) -> bool:
    return SAVE_VERSION.split(".")[0] == save_version.split(".")[0]

func _get_slot_path(slot: int) -> String:
    if slot == AUTOSAVE_SLOT:
        return SAVE_DIR + "autosave"
    return SAVE_DIR + "slot_%d" % slot

func has_save_data(slot: int = -1) -> bool:
    if slot == -1:
        for i in range(MAX_SLOTS):
            if FileAccess.file_exists(_get_slot_path(i + 1) + "/save.json"):
                return true
        return false
    return FileAccess.file_exists(_get_slot_path(slot) + "/save.json")

func delete_save(slot: int) -> bool:
    var dir = DirAccess.open(_get_slot_path(slot))
    if not dir:
        return false
    dir.list_dir_begin()
    var f = dir.get_next()
    while f != "":
        dir.remove(f)
        f = dir.get_next()
    dir.list_dir_end()
    return true

func set_value(key: String, value: Variant) -> void:
    game_data[key] = value

func get_value(key: String, default: Variant = null) -> Variant:
    return game_data.get(key, default)

func _encrypt(data: String) -> String:
    var bytes = data.to_utf8_buffer()
    var key = encryption_password.to_utf8_buffer()
    for i in range(bytes.size()):
        bytes[i] = bytes[i] ^ key[i % key.size()]
    return Marshalls.raw_to_base64(bytes)

func _decrypt(data: String) -> String:
    var bytes = Marshalls.base64_to_raw(data)
    var key = encryption_password.to_utf8_buffer()
    for i in range(bytes.size()):
        bytes[i] = bytes[i] ^ key[i % key.size()]
    return bytes.get_string_from_utf8()
```

## 可保存组件

```gdscript
class_name SaveableComponent
extends Node

@export var save_id: String = ""

func _ready() -> void:
    if save_id.is_empty():
        save_id = str(get_path())
    add_to_group("saveable")

func on_save(save_data: Dictionary) -> void:
    var data = _collect_data()
    if not data.is_empty():
        if not save_data.has("components"):
            save_data["components"] = {}
        save_data["components"][save_id] = data

func on_load(save_data: Dictionary) -> void:
    var components = save_data.get("components", {})
    if components.has(save_id):
        _apply_data(components[save_id])

func _collect_data() -> Dictionary:
    return {}

func _apply_data(_data: Dictionary) -> void:
    pass
```

## 使用示例

```gdscript
# 保存/加载
SaveManager.set_value("player_name", "Hero")
SaveManager.save_game(1)
SaveManager.load_game(1)

# 为节点加存档：继承 SaveableComponent 重写 _collect_data/_apply_data
# 或直接 add_to_group("saveable") + 实现 on_save/on_load
```

## 自动保存

在 `_ready` 里启动 `Timer`，超时触发 `save_game(AUTOSAVE_SLOT)`。
