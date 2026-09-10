# 图片后处理：裁剪 / 压缩 / 格式转换 / 精灵图分割

脚本：`${CODEBUDDY_SKILL_DIR}/scripts/process_image.sh`
依赖：ImageMagick（脚本内置自动安装，支持 winget/brew/apt/dnf/pacman）

## 参数

```
-x/-y/-w/-h   按坐标裁剪（起点+尺寸）
-g <列x行>    精灵图网格分割，导出所有帧到目录
-n <帧索引>   配合 -g，只导出指定帧（从 0 开始）
-p <百分比>   按比例缩放（如 -p 50）
-s <宽x高>    缩放到尺寸（等比：128x0 或 0x128）
-q <1-100>    输出质量（JPEG/WebP，PNG 忽略）
-z <KB>       目标大小上限，自动二分法迭代压缩
-f <格式>     输出格式：png / jpg / webp
-o <路径>     输出路径（-g 时为目录）
```

## 典型示例

```bash
SCRIPT="${CODEBUDDY_SKILL_DIR}/scripts/process_image.sh"

# 压缩到 100KB，转 WebP
bash "$SCRIPT" -z 100 -f webp -o assets/icon.webp assets/icon.png

# 缩放到 256x256，JPEG 质量 85
bash "$SCRIPT" -s 256x256 -q 85 -f jpg -o assets/thumb.jpg assets/bg.png

# 裁剪：从 (128,0) 截取 64x64
bash "$SCRIPT" -x 128 -y 0 -w 64 -h 64 -o assets/frame2.png assets/sheet.png

# 分割精灵图（8列x4行），全部帧输出到目录
bash "$SCRIPT" -g 8x4 -o assets/hero_frames/ assets/hero.png

# 分割精灵图，只取第 0 帧
bash "$SCRIPT" -g 8x4 -n 0 -o assets/idle.png assets/hero.png
```

## 注意

- PNG 为无损格式，`-z` 和 `-q` 无效（自动忽略）
- `-g` 模式下 `-o` 指定的是目录，不是文件名
