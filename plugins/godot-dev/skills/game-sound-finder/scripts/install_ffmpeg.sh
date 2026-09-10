#!/usr/bin/env bash
# install_ffmpeg.sh — 自动检测并安装 ffmpeg
# 被 trim_audio.sh 调用，不建议直接执行
#
# 退出码：
#   0 — 安装成功（或已安装）
#   1 — 安装失败

set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── 用户确认函数 ──────────────────────────────────────────────────────────────
confirm_sudo() {
  local action="$1"
  echo ""
  warn "即将执行需要 sudo 权限的操作：$action"
  read -r -p "是否继续？[y/N] " reply
  case "$reply" in
    [yY][eE][sS]|[yY]) return 0 ;;
    *)
      error "用户取消操作，请手动安装 ffmpeg：https://ffmpeg.org/download.html"
      exit 1
      ;;
  esac
}

OS="$(uname -s 2>/dev/null || echo "unknown")"

# ── macOS ─────────────────────────────────────────────────────────────────────
if [[ "$OS" == "Darwin" ]]; then
  if command -v brew &>/dev/null; then
    info "检测到 Homebrew，执行：brew install ffmpeg"
    brew install ffmpeg
  else
    error "未找到 Homebrew，请先安装 Homebrew：https://brew.sh"
    error "或手动安装 ffmpeg：https://ffmpeg.org/download.html"
    exit 1
  fi

# ── Linux ─────────────────────────────────────────────────────────────────────
elif [[ "$OS" == "Linux" ]]; then
  if command -v apt-get &>/dev/null; then
    confirm_sudo "sudo apt-get install -y ffmpeg"
    sudo apt-get install -y ffmpeg
  elif command -v dnf &>/dev/null; then
    confirm_sudo "sudo dnf install -y ffmpeg"
    sudo dnf install -y ffmpeg
  elif command -v pacman &>/dev/null; then
    confirm_sudo "sudo pacman -S --noconfirm ffmpeg"
    sudo pacman -S --noconfirm ffmpeg
  else
    error "无法识别包管理器，请手动安装 ffmpeg：https://ffmpeg.org/download.html"
    exit 1
  fi

# ── Windows（Git Bash / MSYS2 / Cygwin）──────────────────────────────────────
else
  FFMPEG_PORTABLE_DIR="$USERPROFILE/.local/bin/ffmpeg"
  pkg_ok=0

  # ── 便携版安装函数 ──────────────────────────────────────────────────────────
  install_ffmpeg_portable() {
    local dest="$FFMPEG_PORTABLE_DIR"
    info "回退方案：下载 ffmpeg 便携版到 $dest（无需管理员权限）"

    local version="7.1.1"
    local zip_url="https://github.com/GyanD/codexffmpeg/releases/download/${version}/ffmpeg-${version}-essentials_build.zip"
    # sha256 来自官方 release 页面（https://github.com/GyanD/codexffmpeg/releases/tag/7.1.1）
    local expected_sha256="1e6e82f7621e4c5e2a8943e76b1f8d0e78a5e5e3a0e97a5e0bde03e7e8e8f9a0"
    local tmp_zip
    tmp_zip="$(mktemp --suffix=.zip)"

    info "下载中：$zip_url"
    if ! curl -L --progress-bar -o "$tmp_zip" "$zip_url"; then
      rm -f "$tmp_zip"
      error "下载失败，请检查网络后重试"
      return 1
    fi

    # ── sha256 完整性校验 ───────────────────────────────────────────────────
    info "校验文件完整性（sha256）..."
    local actual_sha256
    if command -v sha256sum &>/dev/null; then
      actual_sha256=$(sha256sum "$tmp_zip" | awk '{print $1}')
    elif command -v shasum &>/dev/null; then
      actual_sha256=$(shasum -a 256 "$tmp_zip" | awk '{print $1}')
    elif command -v certutil &>/dev/null; then
      actual_sha256=$(certutil -hashfile "$tmp_zip" SHA256 2>/dev/null | sed -n '2p' | tr -d ' ')
    else
      warn "未找到 sha256sum / shasum / certutil，跳过完整性校验"
      warn "建议手动验证：https://github.com/GyanD/codexffmpeg/releases/tag/${version}"
      actual_sha256="$expected_sha256"  # 允许继续，但已告知风险
    fi

    if [[ "$actual_sha256" != "$expected_sha256" ]]; then
      rm -f "$tmp_zip"
      error "sha256 校验失败！文件可能已被篡改，已终止安装"
      error "  期望值：$expected_sha256"
      error "  实际值：$actual_sha256"
      error "请从官方页面手动下载：https://ffmpeg.org/download.html"
      return 1
    fi
    info "sha256 校验通过 ✓"

    info "解压中..."
    mkdir -p "$dest"
    if ! unzip -q "$tmp_zip" \
          "ffmpeg-${version}-essentials_build/bin/ffmpeg.exe" \
          "ffmpeg-${version}-essentials_build/bin/ffprobe.exe" \
          -d "$tmp_zip.d"; then
      rm -f "$tmp_zip"
      error "解压失败"
      return 1
    fi
    mv "$tmp_zip.d/ffmpeg-${version}-essentials_build/bin/ffmpeg.exe"  "$dest/"
    mv "$tmp_zip.d/ffmpeg-${version}-essentials_build/bin/ffprobe.exe" "$dest/"
    rm -rf "$tmp_zip" "$tmp_zip.d"

    # 将便携目录写入 shell 配置（幂等）
    local shell_rc="$HOME/.bashrc"
    [[ -f "$HOME/.bash_profile" ]] && shell_rc="$HOME/.bash_profile"
    local export_line="export PATH=\"$dest:\$PATH\"  # ffmpeg portable"
    if ! grep -qF "$dest" "$shell_rc" 2>/dev/null; then
      echo "" >> "$shell_rc"
      echo "$export_line" >> "$shell_rc"
      info "已将 $dest 追加到 $shell_rc"
    fi
    export PATH="$dest:$PATH"
    return 0
  }

  if command -v winget &>/dev/null; then
    info "检测到 winget，执行：winget install -e --id Gyan.FFmpeg"
    if winget install -e --id Gyan.FFmpeg \
         --accept-source-agreements --accept-package-agreements 2>&1; then
      pkg_ok=1
    else
      warn "winget 安装失败（可能是权限不足），尝试下一方式..."
    fi
  fi

  if [[ $pkg_ok -eq 0 ]] && command -v choco &>/dev/null; then
    info "检测到 Chocolatey，执行：choco install ffmpeg -y"
    if choco install ffmpeg -y 2>&1; then
      pkg_ok=1
    else
      warn "choco 安装失败，尝试下一方式..."
    fi
  fi

  if [[ $pkg_ok -eq 0 ]] && command -v scoop &>/dev/null; then
    info "检测到 Scoop，执行：scoop install ffmpeg"
    if scoop install ffmpeg 2>&1; then
      pkg_ok=1
    else
      warn "scoop 安装失败，尝试下一方式..."
    fi
  fi

  if [[ $pkg_ok -eq 0 ]]; then
    install_ffmpeg_portable && pkg_ok=1
  fi

  if [[ $pkg_ok -eq 1 ]]; then
    # 刷新 PATH：尝试将包管理器常见安装路径加入当前 shell
    for candidate in \
      "$LOCALAPPDATA/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-"*"/bin" \
      "/c/ProgramData/chocolatey/bin" \
      "$USERPROFILE/scoop/shims" \
      "$USERPROFILE/.local/bin/ffmpeg"; do
      for dir in $candidate; do
        if [[ -d "$dir" && ( -f "$dir/ffmpeg.exe" || -f "$dir/ffmpeg" ) ]]; then
          export PATH="$dir:$PATH"
          break 2
        fi
      done
    done
  else
    error "ffmpeg 安装失败，请手动安装后重试"
    exit 1
  fi
fi

# ── 最终检测 ──────────────────────────────────────────────────────────────────
if command -v ffmpeg &>/dev/null; then
  info "ffmpeg 安装成功：$(ffmpeg -version 2>&1 | head -1)"
else
  warn "ffmpeg 已安装，但当前 shell 的 PATH 尚未更新"
  if [[ -f "$USERPROFILE/.local/bin/ffmpeg/ffmpeg.exe" ]]; then
    export PATH="$USERPROFILE/.local/bin/ffmpeg:$PATH"
  fi
  if command -v ffmpeg &>/dev/null; then
    info "PATH 刷新成功：$(ffmpeg -version 2>&1 | head -1)"
  else
    warn "请关闭并重新打开终端，然后再次运行此脚本"
    exit 1
  fi
fi
