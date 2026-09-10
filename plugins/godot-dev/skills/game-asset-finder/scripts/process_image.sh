#!/usr/bin/env bash
# process_image.sh — 游戏图片素材裁剪与压缩工具
#
# 依赖：ImageMagick (convert/magick)
# 自动安装逻辑内置，无需手动安装
#
# 用法：
#   bash process_image.sh [选项] <输入文件>
#
# 裁剪选项：
#   -x <像素>      裁剪起点 X 坐标（默认 0）
#   -y <像素>      裁剪起点 Y 坐标（默认 0）
#   -w <像素>      裁剪宽度（不指定则到图片右边缘）
#   -h <像素>      裁剪高度（不指定则到图片下边缘）
#   -g <行x列>     将精灵图分割为 N 行 x M 列，输出每帧（如 -g 4x8）
#   -n <帧索引>    配合 -g 使用，只导出第 N 帧（从 0 开始，不指定则导出所有帧）
#
# 压缩选项：
#   -q <1-100>     输出质量（JPEG/WebP 有效，PNG 忽略）
#   -z <KB>        目标文件大小上限（KB），自动计算压缩参数
#   -s <宽x高>     缩放到指定尺寸，如 -s 128x128（保持比例用 -s 128x0 或 -s 0x128）
#   -p <百分比>    按比例缩放，如 -p 50 表示缩小到 50%
#
# 输出选项：
#   -f <格式>      输出格式：png / jpg / webp（默认保持原格式）
#   -o <路径>      输出文件路径（默认：原文件名加 _out 后缀）
#
# 示例：
#   bash process_image.sh -w 64 -h 64 -x 128 -y 0 -o frame2.png sprite.png
#   bash process_image.sh -g 4x8 -o frames/ spritesheet.png
#   bash process_image.sh -s 256x256 -f webp -z 50 -o icon.webp icon.png
#   bash process_image.sh -p 50 -q 85 -f jpg -o thumb.jpg background.png

set -euo pipefail

# ─────────────────────────────────────────
# 颜色输出
# ─────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ─────────────────────────────────────────
# 自动安装 ImageMagick
# ─────────────────────────────────────────
ensure_imagemagick() {
    # 检测可用命令（ImageMagick 7 用 magick，6 用 convert）
    if command -v magick &>/dev/null; then
        IM_CMD="magick"
        return
    fi
    if command -v convert &>/dev/null; then
        IM_CMD="convert"
        return
    fi

    warn "ImageMagick 未安装，尝试自动安装..."

    if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]] || [[ "$(uname -s)" == MINGW* ]]; then
        # Windows (Git Bash / MSYS2)
        if command -v winget &>/dev/null; then
            info "使用 winget 安装 ImageMagick..."
            winget install --id ImageMagick.ImageMagick -e --silent || true
        elif command -v choco &>/dev/null; then
            info "使用 choco 安装 ImageMagick..."
            choco install imagemagick -y || true
        elif command -v scoop &>/dev/null; then
            info "使用 scoop 安装 ImageMagick..."
            scoop install imagemagick || true
        else
            error "无法自动安装 ImageMagick。请手动安装：https://imagemagick.org/script/download.php"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &>/dev/null; then
            info "使用 brew 安装 ImageMagick..."
            brew install imagemagick
        else
            error "请先安装 Homebrew：https://brew.sh，再运行此脚本"
        fi
    else
        # Linux
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y imagemagick
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y imagemagick
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm imagemagick
        else
            error "无法自动安装 ImageMagick，请手动安装后重试"
        fi
    fi

    # 安装后再检测
    if command -v magick &>/dev/null; then
        IM_CMD="magick"
    elif command -v convert &>/dev/null; then
        IM_CMD="convert"
    else
        error "ImageMagick 安装失败，请手动安装：https://imagemagick.org"
    fi
    info "ImageMagick 安装成功：$IM_CMD"
}

# ─────────────────────────────────────────
# 解析参数
# ─────────────────────────────────────────
OPT_X=""
OPT_Y=""
OPT_W=""
OPT_H=""
OPT_GRID=""
OPT_FRAME=""
OPT_QUALITY=""
OPT_SIZE_KB=""
OPT_SCALE=""
OPT_PERCENT=""
OPT_FORMAT=""
OPT_OUTPUT=""

usage() {
    sed -n '3,35p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

while getopts ":x:y:w:h:g:n:q:z:s:p:f:o:H" opt; do
    case $opt in
        x) OPT_X="$OPTARG" ;;
        y) OPT_Y="$OPTARG" ;;
        w) OPT_W="$OPTARG" ;;
        h) OPT_H="$OPTARG" ;;
        g) OPT_GRID="$OPTARG" ;;
        n) OPT_FRAME="$OPTARG" ;;
        q) OPT_QUALITY="$OPTARG" ;;
        z) OPT_SIZE_KB="$OPTARG" ;;
        s) OPT_SCALE="$OPTARG" ;;
        p) OPT_PERCENT="$OPTARG" ;;
        f) OPT_FORMAT="$OPTARG" ;;
        o) OPT_OUTPUT="$OPTARG" ;;
        H) usage ;;
        :) error "选项 -$OPTARG 需要参数" ;;
        \?) error "未知选项 -$OPTARG，使用 -H 查看帮助" ;;
    esac
done
shift $((OPTIND - 1))

[[ $# -eq 0 ]] && error "请提供输入文件路径。使用 -H 查看帮助"
INPUT="$1"
[[ ! -f "$INPUT" ]] && error "输入文件不存在：$INPUT"

# ─────────────────────────────────────────
# 确保 ImageMagick 可用
# ─────────────────────────────────────────
ensure_imagemagick

# ─────────────────────────────────────────
# 推断输出路径和格式
# ─────────────────────────────────────────
INPUT_EXT="${INPUT##*.}"
INPUT_EXT_LOWER="${INPUT_EXT,,}"
INPUT_BASE="${INPUT%.*}"
INPUT_BASENAME="$(basename "$INPUT_BASE")"

OUT_EXT="${OPT_FORMAT:-$INPUT_EXT_LOWER}"

if [[ -n "$OPT_OUTPUT" ]]; then
    OUTPUT="$OPT_OUTPUT"
else
    OUTPUT="${INPUT_BASE}_out.${OUT_EXT}"
fi

# ─────────────────────────────────────────
# 获取原始图片尺寸
# ─────────────────────────────────────────
get_dimensions() {
    $IM_CMD identify -format "%wx%h" "$1" 2>/dev/null
}

ORIG_DIM=$(get_dimensions "$INPUT")
ORIG_W="${ORIG_DIM%x*}"
ORIG_H="${ORIG_DIM#*x}"
info "原始图片：$INPUT (${ORIG_W}x${ORIG_H})"

# ─────────────────────────────────────────
# 模式 1：精灵图网格分割 (-g)
# ─────────────────────────────────────────
if [[ -n "$OPT_GRID" ]]; then
    GRID_COLS="${OPT_GRID%x*}"
    GRID_ROWS="${OPT_GRID#*x}"
    FRAME_W=$((ORIG_W / GRID_COLS))
    FRAME_H=$((ORIG_H / GRID_ROWS))
    TOTAL_FRAMES=$((GRID_COLS * GRID_ROWS))

    info "精灵图分割：${GRID_COLS}列 x ${GRID_ROWS}行，每帧 ${FRAME_W}x${FRAME_H}，共 ${TOTAL_FRAMES} 帧"

    # 确定输出目录
    if [[ -n "$OPT_OUTPUT" ]]; then
        OUT_DIR="$OPT_OUTPUT"
    else
        OUT_DIR="${INPUT_BASE}_frames"
    fi
    mkdir -p "$OUT_DIR"

    if [[ -n "$OPT_FRAME" ]]; then
        # 只导出指定帧
        FRAME_IDX="$OPT_FRAME"
        COL=$((FRAME_IDX % GRID_COLS))
        ROW=$((FRAME_IDX / GRID_COLS))
        CROP_X=$((COL * FRAME_W))
        CROP_Y=$((ROW * FRAME_H))
        OUT_FILE="${OUT_DIR}/frame_${FRAME_IDX}.${OUT_EXT}"
        $IM_CMD "$INPUT" -crop "${FRAME_W}x${FRAME_H}+${CROP_X}+${CROP_Y}" +repage "$OUT_FILE"
        info "导出帧 #${FRAME_IDX} → $OUT_FILE"
    else
        # 导出所有帧
        for ((i=0; i<TOTAL_FRAMES; i++)); do
            COL=$((i % GRID_COLS))
            ROW=$((i / GRID_COLS))
            CROP_X=$((COL * FRAME_W))
            CROP_Y=$((ROW * FRAME_H))
            OUT_FILE="${OUT_DIR}/frame_$(printf '%03d' $i).${OUT_EXT}"
            $IM_CMD "$INPUT" -crop "${FRAME_W}x${FRAME_H}+${CROP_X}+${CROP_Y}" +repage "$OUT_FILE"
        done
        info "已导出 ${TOTAL_FRAMES} 帧到 ${OUT_DIR}/"
    fi

    # 统计
    FILE_COUNT=$(ls "$OUT_DIR"/frame_*.${OUT_EXT} 2>/dev/null | wc -l)
    echo ""
    echo "分割完成！共 ${FILE_COUNT} 帧，保存至：${OUT_DIR}/"
    exit 0
fi

# ─────────────────────────────────────────
# 构建 ImageMagick 参数链
# ─────────────────────────────────────────
IM_ARGS=()

# 1. 裁剪
if [[ -n "$OPT_W" || -n "$OPT_H" || -n "$OPT_X" || -n "$OPT_Y" ]]; then
    CX="${OPT_X:-0}"
    CY="${OPT_Y:-0}"
    CW="${OPT_W:-$((ORIG_W - CX))}"
    CH="${OPT_H:-$((ORIG_H - CY))}"
    IM_ARGS+=(-crop "${CW}x${CH}+${CX}+${CY}" +repage)
    info "裁剪：偏移(${CX},${CY}) 尺寸 ${CW}x${CH}"
fi

# 2. 缩放（按百分比优先于按尺寸）
if [[ -n "$OPT_PERCENT" ]]; then
    IM_ARGS+=(-resize "${OPT_PERCENT}%")
    info "缩放：${OPT_PERCENT}%"
elif [[ -n "$OPT_SCALE" ]]; then
    # 支持 128x0 或 0x128 写法（保持比例）
    SCALE_SPEC="$OPT_SCALE"
    if [[ "$SCALE_SPEC" == *"x0" ]]; then
        W="${SCALE_SPEC%x0}"
        IM_ARGS+=(-resize "${W}")
    elif [[ "$SCALE_SPEC" == "0x"* ]]; then
        H="${SCALE_SPEC#0x}"
        IM_ARGS+=(-resize "x${H}")
    else
        IM_ARGS+=(-resize "${SCALE_SPEC}!")
    fi
    info "缩放尺寸：${SCALE_SPEC}"
fi

# 3. 质量（JPEG/WebP）
if [[ -n "$OPT_QUALITY" ]]; then
    IM_ARGS+=(-quality "$OPT_QUALITY")
    info "输出质量：${OPT_QUALITY}"
fi

# 4. PNG 去除元数据（减小体积）
if [[ "$OUT_EXT" == "png" ]]; then
    IM_ARGS+=(-strip)
fi

# ─────────────────────────────────────────
# 执行转换
# ─────────────────────────────────────────
info "输出文件：$OUTPUT"
$IM_CMD "$INPUT" "${IM_ARGS[@]}" "${OUT_EXT}:${OUTPUT}"

# ─────────────────────────────────────────
# 目标大小压缩（-z）：二分法迭代调整质量
# ─────────────────────────────────────────
if [[ -n "$OPT_SIZE_KB" ]]; then
    TARGET_BYTES=$((OPT_SIZE_KB * 1024))
    ACTUAL_BYTES=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null || echo 0)

    if [[ "$OUT_EXT" == "png" ]]; then
        warn "PNG 为无损格式，-z 大小限制对 PNG 输出无效（已忽略）"
    elif [[ $ACTUAL_BYTES -gt $TARGET_BYTES ]]; then
        info "当前大小 $((ACTUAL_BYTES/1024))KB > 目标 ${OPT_SIZE_KB}KB，开始迭代压缩..."
        Q_LOW=1; Q_HIGH=95; Q_BEST=50
        for _ in $(seq 1 12); do
            Q_MID=$(( (Q_LOW + Q_HIGH) / 2 ))
            $IM_CMD "$INPUT" "${IM_ARGS[@]}" -quality "$Q_MID" "${OUT_EXT}:${OUTPUT}" 2>/dev/null
            BYTES=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null || echo 0)
            if [[ $BYTES -le $TARGET_BYTES ]]; then
                Q_BEST=$Q_MID; Q_LOW=$Q_MID
            else
                Q_HIGH=$Q_MID
            fi
        done
        # 用找到的最佳质量最终输出
        $IM_CMD "$INPUT" "${IM_ARGS[@]}" -quality "$Q_BEST" "${OUT_EXT}:${OUTPUT}"
        FINAL_BYTES=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null || echo 0)
        info "压缩完成：质量=${Q_BEST}，大小 $((FINAL_BYTES/1024))KB（目标 ${OPT_SIZE_KB}KB）"
    else
        info "当前大小 $((ACTUAL_BYTES/1024))KB 已在目标 ${OPT_SIZE_KB}KB 以内，无需额外压缩"
    fi
fi

# ─────────────────────────────────────────
# 结果报告
# ─────────────────────────────────────────
FINAL_BYTES=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null || echo 0)
FINAL_DIM=$(get_dimensions "$OUTPUT")
echo ""
echo "处理完成！"
echo "  输入：$INPUT (${ORIG_W}x${ORIG_H})"
echo "  输出：$OUTPUT (${FINAL_DIM}，$((FINAL_BYTES/1024))KB)"
