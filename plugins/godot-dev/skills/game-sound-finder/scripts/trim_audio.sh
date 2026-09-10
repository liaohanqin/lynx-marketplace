#!/usr/bin/env bash
# trim_audio.sh — 音频裁剪 / 压缩 / 格式转换工具
# 依赖：ffmpeg（脚本会自动调用同目录下的 install_ffmpeg.sh 安装）
# 用法：bash trim_audio.sh [选项] <输入文件>
#
# 选项：
#   -s, --start <时间>        裁剪起点，默认 0（格式：秒数 或 HH:MM:SS）
#   -d, --duration <时间>     持续时长（与 -e 二选一）
#   -e, --end <时间>          结束时间点（与 -d 二选一）
#   -z, --target-size <KB>   目标文件大小上限（KB），自动计算码率
#   -f, --format <格式>       输出格式：mp3 / wav / ogg（默认保持原格式）
#   -o, --output <路径>       输出文件路径（默认：原文件名_out.扩展名）
#   -h, --help               显示帮助

set -euo pipefail

# ── 颜色输出 ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── 帮助 ────────────────────────────────────────────────────────────────────
usage() {
  cat <<'EOF'
用法: bash trim_audio.sh [选项] <输入文件>

选项:
  -s, --start <时间>        裁剪起点（默认 0）
                            格式：秒数（如 30）或 HH:MM:SS（如 00:00:30）
  -d, --duration <时间>     持续时长（如 10 表示10秒）
  -e, --end <时间>          结束时间点（-d 与 -e 二选一）
  -z, --target-size <KB>   目标文件大小上限（KB），自动压缩码率
                            注意：WAV 为无损格式，此选项对 WAV 输出无效
  -f, --format <格式>       输出格式：mp3 / wav / ogg（默认保持原格式）
  -o, --output <路径>       输出文件路径
  -h, --help               显示此帮助

示例:
  # 截取前10秒，压缩到80KB以内，输出mp3
  bash trim_audio.sh -s 0 -d 10 -f mp3 -z 80 -o out.mp3 input.wav

  # 截取第5~35秒片段，压缩到200KB
  bash trim_audio.sh -s 5 -e 35 -z 200 input.mp3

  # 仅格式转换（wav → ogg）
  bash trim_audio.sh -f ogg -o output.ogg input.wav

  # 仅按大小压缩，不裁剪
  bash trim_audio.sh -z 500 input.mp3
EOF
}

# ── 默认参数 ─────────────────────────────────────────────────────────────────
START=""
DURATION=""
END_TIME=""
TARGET_SIZE_KB=""
FORMAT=""
OUTPUT=""
INPUT=""

# ── 解析参数 ─────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--start)        START="$2";         shift 2 ;;
    -d|--duration)     DURATION="$2";      shift 2 ;;
    -e|--end)          END_TIME="$2";      shift 2 ;;
    -z|--target-size)  TARGET_SIZE_KB="$2";shift 2 ;;
    -f|--format)       FORMAT="$2";        shift 2 ;;
    -o|--output)       OUTPUT="$2";        shift 2 ;;
    -h|--help)         usage; exit 0 ;;
    -*)
      error "未知选项：$1"
      usage
      exit 1
      ;;
    *)
      if [[ -z "$INPUT" ]]; then
        INPUT="$1"
      else
        error "多余的参数：$1"
        exit 1
      fi
      shift
      ;;
  esac
done

# ── 前置检查 ─────────────────────────────────────────────────────────────────
if [[ -z "$INPUT" ]]; then
  error "缺少输入文件"
  usage
  exit 1
fi

if [[ ! -f "$INPUT" ]]; then
  error "输入文件不存在：$INPUT"
  exit 1
fi

# ── ffmpeg 检测与自动安装 ─────────────────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
  warn "未找到 ffmpeg，尝试自动安装..."
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  INSTALL_SCRIPT="$SCRIPT_DIR/install_ffmpeg.sh"

  if [[ ! -f "$INSTALL_SCRIPT" ]]; then
    error "未找到安装脚本：$INSTALL_SCRIPT"
    error "请手动安装 ffmpeg：https://ffmpeg.org/download.html"
    exit 1
  fi

  bash "$INSTALL_SCRIPT"

  if ! command -v ffmpeg &>/dev/null; then
    error "ffmpeg 安装后仍无法在 PATH 中找到，请重启终端后重试"
    exit 1
  fi
fi

if [[ -n "$DURATION" && -n "$END_TIME" ]]; then
  error "-d (时长) 和 -e (结束时间) 不能同时使用"
  exit 1
fi

# ── 推导输出路径 ──────────────────────────────────────────────────────────────
BASENAME="${INPUT%.*}"
INPUT_EXT="${INPUT##*.}"
OUT_EXT="${FORMAT:-$INPUT_EXT}"
OUT_EXT="${OUT_EXT,,}"  # 转小写

if [[ -z "$OUTPUT" ]]; then
  OUTPUT="${BASENAME}_out.${OUT_EXT}"
fi

# ── 计算实际输出时长（用于码率计算）─────────────────────────────────────────
# 先用 ffprobe 获取原始时长（秒）
get_duration_seconds() {
  ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$1" 2>/dev/null | awk '{printf "%.3f", $1}'
}

# 将 HH:MM:SS 或纯秒数转为秒数（浮点）
to_seconds() {
  local t="$1"
  if [[ "$t" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "$t"
  elif [[ "$t" =~ ^([0-9]+):([0-9]{2}):([0-9]{2}(\.[0-9]+)?)$ ]]; then
    awk "BEGIN { printf \"%.3f\", ${BASH_REMATCH[1]}*3600 + ${BASH_REMATCH[2]}*60 + ${BASH_REMATCH[3]} }"
  elif [[ "$t" =~ ^([0-9]+):([0-9]{2}(\.[0-9]+)?)$ ]]; then
    awk "BEGIN { printf \"%.3f\", ${BASH_REMATCH[1]}*60 + ${BASH_REMATCH[2]} }"
  else
    error "无法解析时间格式：$t（支持：秒数 或 HH:MM:SS 或 MM:SS）"
    exit 1
  fi
}

ORIGINAL_DURATION=$(get_duration_seconds "$INPUT")
info "原始文件：$INPUT（时长 ${ORIGINAL_DURATION}s）"

# 计算裁剪后的输出时长
START_SEC=0
if [[ -n "$START" ]]; then
  START_SEC=$(to_seconds "$START")
fi

OUTPUT_DURATION="$ORIGINAL_DURATION"
if [[ -n "$DURATION" ]]; then
  OUTPUT_DURATION=$(to_seconds "$DURATION")
elif [[ -n "$END_TIME" ]]; then
  END_SEC=$(to_seconds "$END_TIME")
  OUTPUT_DURATION=$(awk "BEGIN { printf \"%.3f\", $END_SEC - $START_SEC }")
else
  # 无裁剪参数：从 START 到结尾
  OUTPUT_DURATION=$(awk "BEGIN { printf \"%.3f\", $ORIGINAL_DURATION - $START_SEC }")
fi

if awk "BEGIN { exit ($OUTPUT_DURATION <= 0) }"; then
  : # 正常
else
  error "输出时长计算结果为 0 或负数，请检查 -s/-d/-e 参数"
  exit 1
fi

info "输出时长：${OUTPUT_DURATION}s"

# ── 组装 ffmpeg 参数 ──────────────────────────────────────────────────────────
FF_ARGS=(-y -i "$INPUT")

# 裁剪参数（放在 -i 之后保证精度）
if [[ -n "$START" && "$START" != "0" && "$START" != "0.0" ]]; then
  FF_ARGS+=(-ss "$START")
fi

if [[ -n "$DURATION" ]]; then
  FF_ARGS+=(-t "$DURATION")
elif [[ -n "$END_TIME" ]]; then
  FF_ARGS+=(-to "$END_TIME")
elif [[ -n "$START" && "$START" != "0" && "$START" != "0.0" ]]; then
  : # 从 START 到结尾，不加 -t
fi

# 格式 / 编码器
case "$OUT_EXT" in
  mp3)
    FF_ARGS+=(-c:a libmp3lame)
    ;;
  ogg)
    FF_ARGS+=(-c:a libvorbis)
    ;;
  wav)
    FF_ARGS+=(-c:a pcm_s16le)
    if [[ -n "$TARGET_SIZE_KB" ]]; then
      warn "WAV 为无损格式，忽略 -z（目标大小）选项"
      TARGET_SIZE_KB=""
    fi
    ;;
  *)
    # 其他格式交给 ffmpeg 自动选择编码器
    ;;
esac

# 码率压缩（-z）
if [[ -n "$TARGET_SIZE_KB" ]]; then
  if ! [[ "$TARGET_SIZE_KB" =~ ^[0-9]+$ ]]; then
    error "-z 参数必须是正整数（KB）"
    exit 1
  fi

  BITRATE=$(awk "BEGIN {
    b = int($TARGET_SIZE_KB * 8 / $OUTPUT_DURATION * 0.95)
    if (b < 8)   b = 8
    if (b > 320) b = 320
    print b
  }")

  info "目标大小：${TARGET_SIZE_KB}KB → 计算码率：${BITRATE}kbps"
  FF_ARGS+=(-b:a "${BITRATE}k")
fi

# 输出文件
FF_ARGS+=("$OUTPUT")

# ── 执行 ─────────────────────────────────────────────────────────────────────
info "执行命令：ffmpeg ${FF_ARGS[*]}"
echo ""

if ffmpeg "${FF_ARGS[@]}" 2>&1; then
  echo ""
  if [[ -f "$OUTPUT" ]]; then
    OUT_SIZE=$(awk "BEGIN { printf \"%.1f\", $(wc -c < "$OUTPUT") / 1024 }")
    OUT_DUR=$(get_duration_seconds "$OUTPUT")
    info "完成！输出文件：$OUTPUT"
    info "  时长：${OUT_DUR}s  |  大小：${OUT_SIZE}KB"
    if [[ -n "$TARGET_SIZE_KB" ]]; then
      ACTUAL_KB=$(awk "BEGIN { printf \"%.0f\", $(wc -c < "$OUTPUT") / 1024 }")
      if awk "BEGIN { exit ($ACTUAL_KB <= $TARGET_SIZE_KB) }"; then
        warn "实际大小 ${ACTUAL_KB}KB 超过目标 ${TARGET_SIZE_KB}KB，可尝试降低码率或缩短时长"
      else
        info "  大小检查：${ACTUAL_KB}KB ≤ ${TARGET_SIZE_KB}KB ✓"
      fi
    fi
  fi
else
  error "ffmpeg 执行失败"
  exit 1
fi
