#!/usr/bin/env bash
# svg_to_png.sh — SVG 转 PNG 工具
#
# 依赖（按优先级自动检测）：
#   1. Inkscape          — 最高质量，支持复杂 SVG
#   2. rsvg-convert      — librsvg，轻量快速
#   3. Node.js + resvg-js — Windows 友好，自动安装
#   4. ImageMagick       — 通用备选
#
# 用法：
#   bash svg_to_png.sh [选项] <输入.svg> [输入2.svg ...]
#
# 选项：
#   -w <像素>    输出宽度（默认保持 SVG 原始宽度）
#   -h <像素>    输出高度（默认保持 SVG 原始高度）
#   -o <目录>    输出目录（默认：与输入文件同目录）
#   -s <倍数>    缩放倍数，如 -s 2 输出 2x 分辨率（与 -w/-h 互斥）
#   -H           显示帮助
#
# 示例：
#   bash svg_to_png.sh icon.svg
#   bash svg_to_png.sh -w 128 -h 128 icon.svg
#   bash svg_to_png.sh -s 2 -o assets/ icon.svg button.svg healthbar.svg

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ─────────────────────────────────────────
# 检测并安装转换工具
# ─────────────────────────────────────────
CONV_TOOL=""

detect_tool() {
    if command -v inkscape &>/dev/null; then
        CONV_TOOL="inkscape"
    elif command -v rsvg-convert &>/dev/null; then
        CONV_TOOL="rsvg"
    elif command -v node &>/dev/null; then
        # 检查 resvg-js 是否已全局安装
        local GMOD
        GMOD=$(node -e "try{process.stdout.write(require('child_process').execSync('npm root -g').toString().trim())}catch(e){}" 2>/dev/null || echo "")
        if [[ -n "$GMOD" && -d "$GMOD/@resvg/resvg-js" ]]; then
            CONV_TOOL="resvg-js"
            RESVG_JS_PATH="$GMOD/@resvg/resvg-js"
        else
            CONV_TOOL="node-pending"  # node 可用但 resvg-js 未装
        fi
    elif command -v magick &>/dev/null; then
        CONV_TOOL="imagemagick"
    elif command -v convert &>/dev/null && convert --version 2>&1 | grep -qi "imagemagick"; then
        CONV_TOOL="imagemagick"
    fi
}

install_tool() {
    warn "未检测到 SVG 转换工具，尝试自动安装..."

    # 优先尝试 Node.js + resvg-js（跨平台，Windows 友好）
    if command -v node &>/dev/null; then
        info "检测到 Node.js，安装 @resvg/resvg-js..."
        npm install -g @resvg/resvg-js --registry https://registry.npmjs.org 2>/dev/null || \
        npm install -g @resvg/resvg-js 2>/dev/null || true
        detect_tool
        [[ "$CONV_TOOL" == "resvg-js" ]] && return
    fi

    if [[ "$OSTYPE" == "msys"* ]] || [[ "$(uname -s)" == MINGW* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
        if command -v choco &>/dev/null; then
            choco install inkscape -y 2>/dev/null || true
        elif command -v scoop &>/dev/null; then
            scoop install inkscape 2>/dev/null || true
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        command -v brew &>/dev/null && brew install librsvg
    else
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y librsvg2-bin
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y librsvg2-tools
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm librsvg
        fi
    fi
    detect_tool
    [[ -z "$CONV_TOOL" || "$CONV_TOOL" == "node-pending" ]] && \
        error "无法自动安装 SVG 转换工具。请手动安装 Inkscape 或运行：npm install -g @resvg/resvg-js"
    info "已找到工具：$CONV_TOOL"
}

# ─────────────────────────────────────────
# 解析参数
# ─────────────────────────────────────────
OPT_W=""
OPT_H=""
OPT_SCALE=""
OPT_OUTDIR=""

usage() {
    sed -n '3,18p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

while getopts ":w:h:o:s:H" opt; do
    case $opt in
        w) OPT_W="$OPTARG" ;;
        h) OPT_H="$OPTARG" ;;
        o) OPT_OUTDIR="$OPTARG" ;;
        s) OPT_SCALE="$OPTARG" ;;
        H) usage ;;
        :) error "选项 -$OPTARG 需要参数" ;;
        \?) error "未知选项 -$OPTARG" ;;
    esac
done
shift $((OPTIND - 1))

[[ $# -eq 0 ]] && error "请提供至少一个 SVG 文件。使用 -H 查看帮助"

# ─────────────────────────────────────────
# 检测工具
# ─────────────────────────────────────────
CONV_TOOL=""
RESVG_JS_PATH=""

detect_tool
[[ -z "$CONV_TOOL" || "$CONV_TOOL" == "node-pending" ]] && install_tool

info "使用工具：$CONV_TOOL"

# ─────────────────────────────────────────
# 转换函数
# ─────────────────────────────────────────
convert_svg() {
    local INPUT="$1"
    local OUTPUT="$2"

    case "$CONV_TOOL" in
        inkscape)
            local ARGS=("--export-type=png" "--export-filename=$OUTPUT")
            [[ -n "$OPT_W" ]] && ARGS+=("--export-width=$OPT_W")
            [[ -n "$OPT_H" ]] && ARGS+=("--export-height=$OPT_H")
            if [[ -n "$OPT_SCALE" ]]; then
                local DIM
                DIM=$(inkscape --query-width "$INPUT" 2>/dev/null || echo "64")
                local SW
                SW=$(echo "$DIM * $OPT_SCALE" | bc 2>/dev/null || echo "$((${DIM%.*} * OPT_SCALE))")
                ARGS+=("--export-width=${SW%.*}")
            fi
            inkscape "${ARGS[@]}" "$INPUT" 2>/dev/null
            ;;
        rsvg)
            local ARGS=("-f" "png" "-o" "$OUTPUT")
            [[ -n "$OPT_W" ]] && ARGS+=("-w" "$OPT_W")
            [[ -n "$OPT_H" ]] && ARGS+=("-h" "$OPT_H")
            [[ -n "$OPT_SCALE" ]] && ARGS+=("-z" "$OPT_SCALE")
            rsvg-convert "${ARGS[@]}" "$INPUT"
            ;;
        resvg-js)
            # 用 Node.js + @resvg/resvg-js 转换
            local FIT_OBJ="{}"
            if [[ -n "$OPT_W" ]]; then
                FIT_OBJ="{ mode: 'width', value: ${OPT_W} }"
            elif [[ -n "$OPT_H" ]]; then
                FIT_OBJ="{ mode: 'height', value: ${OPT_H} }"
            elif [[ -n "$OPT_SCALE" ]]; then
                FIT_OBJ="{ mode: 'zoom', value: ${OPT_SCALE} }"
            fi
            node -e "
const { Resvg } = require('${RESVG_JS_PATH}');
const fs = require('fs');
const svg = fs.readFileSync('${INPUT}');
const resvg = new Resvg(svg, { fitTo: ${FIT_OBJ} });
const png = resvg.render().asPng();
fs.writeFileSync('${OUTPUT}', png);
"
            ;;
        imagemagick)
            local IM_CMD="magick"
            command -v magick &>/dev/null || IM_CMD="convert"
            local RESIZE=""
            if [[ -n "$OPT_W" && -n "$OPT_H" ]]; then
                RESIZE="${OPT_W}x${OPT_H}!"
            elif [[ -n "$OPT_W" ]]; then
                RESIZE="${OPT_W}"
            elif [[ -n "$OPT_H" ]]; then
                RESIZE="x${OPT_H}"
            elif [[ -n "$OPT_SCALE" ]]; then
                RESIZE="${OPT_SCALE}00%"
            fi
            if [[ -n "$RESIZE" ]]; then
                $IM_CMD -background none -density 300 "$INPUT" -resize "$RESIZE" "$OUTPUT"
            else
                $IM_CMD -background none -density 300 "$INPUT" "$OUTPUT"
            fi
            ;;
    esac
}

# ─────────────────────────────────────────
# 批量处理
# ─────────────────────────────────────────
CONVERTED=0
FAILED=0

for SVG in "$@"; do
    [[ ! -f "$SVG" ]] && { warn "文件不存在，跳过：$SVG"; ((FAILED++)); continue; }

    BASENAME="$(basename "${SVG%.svg}")"
    if [[ -n "$OPT_OUTDIR" ]]; then
        mkdir -p "$OPT_OUTDIR"
        OUTPUT="${OPT_OUTDIR}/${BASENAME}.png"
    else
        OUTPUT="$(dirname "$SVG")/${BASENAME}.png"
    fi

    info "转换：$SVG → $OUTPUT"
    if convert_svg "$SVG" "$OUTPUT"; then
        SIZE=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null || echo "?")
        info "完成：$OUTPUT ($((SIZE / 1024))KB)"
        ((CONVERTED++))
    else
        warn "转换失败：$SVG"
        ((FAILED++))
    fi
done

echo ""
echo "转换完成：成功 ${CONVERTED} 个，失败 ${FAILED} 个"
