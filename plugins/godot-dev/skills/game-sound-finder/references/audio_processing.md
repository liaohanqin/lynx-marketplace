# 音频后处理：裁剪 / 压缩 / 格式转换

调用脚本：`bash "${CODEBUDDY_SKILL_DIR}/scripts/trim_audio.sh"`

ffmpeg 若未安装，脚本会自动通过 `scripts/install_ffmpeg.sh` 安装：
- Windows：winget → choco → scoop → 便携版（含 sha256 校验）
- macOS：`brew install ffmpeg`
- Linux：apt / dnf / pacman（执行 sudo 前会请求用户确认）

## 参数速查

```
-s <时间>    裁剪起点（秒数 或 HH:MM:SS），默认 0
-d <时间>    持续时长（与 -e 二选一）
-e <时间>    结束时间点（与 -d 二选一）
-z <KB>      目标文件大小上限（KB），自动计算压缩码率
-f <格式>    输出格式：mp3 / wav / ogg（默认保持原格式）
-o <路径>    输出文件路径（默认：原名_out.扩展名）
-h           显示帮助
```

## 典型示例

```bash
SCRIPT="${CODEBUDDY_SKILL_DIR}/scripts/trim_audio.sh"

# 截取前10秒，压缩到80KB，输出mp3
bash "$SCRIPT" -s 0 -d 10 -f mp3 -z 80 -o sounds/click_short.mp3 sounds/click.wav

# 截取第5~35秒，压缩到200KB以内
bash "$SCRIPT" -s 5 -e 35 -z 200 sounds/bgm.mp3

# 仅格式转换（wav → ogg）
bash "$SCRIPT" -f ogg -o sounds/bgm.ogg sounds/bgm.wav

# 仅压缩大小（500KB以内）
bash "$SCRIPT" -z 500 sounds/bgm.mp3

# 截取 + 转格式 + 压缩，三合一
bash "$SCRIPT" -s 10 -d 30 -f ogg -z 300 -o sounds/loop.ogg sounds/bgm.mp3
```

## 注意事项

- WAV 为无损格式，`-z` 对 WAV 输出无效，会自动忽略
- `-d` 和 `-e` 不能同时使用
- 时间格式支持：纯秒数（`30`）、MM:SS（`1:30`）、HH:MM:SS（`00:01:30`）
