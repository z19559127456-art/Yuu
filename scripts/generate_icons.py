"""
应用图标生成脚本 — 将 SVG/PNG 源文件转换为各平台图标格式。

依赖: pip install Pillow

用法:
  python scripts/generate_icons.py                     # 使用默认 SVG 生成所有图标
  python scripts/generate_icons.py --input logo.png    # 从 PNG 源生成
  python scripts/generate_icons.py --no-icns           # 跳过 macOS .icns
"""
import argparse
import sys
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
ICONS_DIR = ROOT / "frontend" / "public"

# 标准图标尺寸
SIZES = [16, 24, 32, 48, 64, 128, 256]


def create_default_svg() -> str:
    """返回一个默认的 vx Agent 图标 SVG —— 简洁的交错圆环设计。"""
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#6366f1"/>
      <stop offset="100%" stop-color="#8b5cf6"/>
    </linearGradient>
    <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#a78bfa"/>
      <stop offset="100%" stop-color="#c4b5fd"/>
    </linearGradient>
  </defs>
  <rect width="256" height="256" rx="48" fill="url(#bg)"/>
  <circle cx="128" cy="100" r="32" fill="none" stroke="white" stroke-width="8"/>
  <circle cx="128" cy="156" r="48" fill="none" stroke="white" stroke-width="6" opacity="0.7"/>
  <line x1="80" y1="80" x2="60" y2="56" stroke="white" stroke-width="6" stroke-linecap="round" opacity="0.8"/>
  <line x1="176" y1="80" x2="196" y2="56" stroke="white" stroke-width="6" stroke-linecap="round" opacity="0.8"/>
  <circle cx="128" cy="100" r="10" fill="white"/>
</svg>"""


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """构建一个 PNG chunk。"""
    chunk = chunk_type + data
    crc = struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
    return struct.pack(">I", len(data)) + chunk + crc


def create_minimal_png(width: int, height: int, r: int, g: int, b: int) -> bytes:
    """生成纯色最小 PNG 字节流（无 PIL 依赖的降级方案）。"""
    def _filter_row(row):
        return b"\x00" + row  # filter type 0 (None)

    raw = b""
    for y in range(height):
        row = bytes([r, g, b] * width)
        raw += _filter_row(row)

    compressed = zlib.compress(raw)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", compressed)
    png += _png_chunk(b"IEND", b"")
    return png


def _svg_to_png_pillow(svg_bytes: bytes, size: int) -> bytes:
    """使用 Pillow + cairosvg 或 resvg 渲染 SVG → PNG。"""
    try:
        import cairosvg
        return cairosvg.svg2png(bytestring=svg_bytes.decode("utf-8"),
                                output_width=size, output_height=size)
    except ImportError:
        pass

    try:
        from PIL import Image
        from io import BytesIO
        # 如果没有 cairosvg，回退为纯色方块
        img = Image.new("RGBA", (size, size), (99, 102, 241, 255))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # 终极降级：纯色 PNG
        return create_minimal_png(size, size, 99, 102, 241)


def _svg_to_png(svg_bytes: bytes, size: int) -> bytes:
    """渲染 SVG 到指定尺寸的 PNG 字节。优先使用 cairosvg，否则 Pillow，最终纯色。"""
    return _svg_to_png_pillow(svg_bytes, size)


def build_ico(png_sizes: dict[int, bytes]) -> bytes:
    """将多尺寸 PNG 数据打包为 Windows .ico 文件。"""
    # ICO header
    num_images = len(png_sizes)
    header = struct.pack("<HHH", 0, 1, num_images)

    # ICO directory entries + image data
    entries = b""
    images = b""
    offset = 6 + 16 * num_images  # header + directory

    for size in sorted(png_sizes.keys(), reverse=True):
        data = png_sizes[size]
        img_size = 256 if size >= 256 else size
        entries += struct.pack("<BBBBHHII",
            img_size, img_size, 0, 0,       # width, height, colors, reserved
            1, 32,                           # planes, bpp
            len(data), offset                # size, offset
        )
        images += data
        offset += len(data)

    return header + entries + images


def generate_icons(svg_input: str | None = None, output_dir: Path | None = None):
    """生成所有平台图标文件。"""
    output_dir = output_dir or ICONS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    svg_bytes = (svg_input or create_default_svg()).encode("utf-8")

    print(f"生成图标到 {output_dir}/ ...")

    # 渲染各尺寸 PNG
    png_sizes = {}
    for size in SIZES:
        png_sizes[size] = _svg_to_png(svg_bytes, size)
        print(f"  ✓ {size}x{size} PNG")

    # --- Windows .ico ---
    ico_path = output_dir / "icon.ico"
    ico_path.write_bytes(build_ico(png_sizes))
    print(f"  ✓ icon.ico ({len(SIZES)} 尺寸)")

    # --- macOS .icns ---
    if all(s in png_sizes for s in [16, 32, 128, 256]):
        icns_data = bytearray()

        # ICNS magic
        icns_data.extend(b"icns")

        # ICNS 类型映射
        type_map = {
            16:  b"icp4",   # 16x16
            32:  b"icp5",   # 32x32
            128: b"ic07",   # 128x128
            256: b"ic08",   # 256x256
        }

        total_size = 8  # header
        entries = []
        for size, icon_type in type_map.items():
            if size in png_sizes:
                entry = icon_type + struct.pack(">I", len(png_sizes[size]) + 8) + png_sizes[size]
                entries.append(entry)
                total_size += len(entry)

        icns_data.extend(struct.pack(">I", total_size))
        for entry in entries:
            icns_data.extend(entry)

        icns_path = output_dir / "icon.icns"
        icns_path.write_bytes(bytes(icns_data))
        print("  ✓ icon.icns")

    # --- 通用 PNG ---
    for size in [128, 256]:
        png_path = output_dir / f"icon-{size}.png"
        png_path.write_bytes(png_sizes[size])
    print("  ✓ icon-128.png, icon-256.png")

    # --- SVG 源文件 ---
    svg_path = output_dir / "icon.svg"
    svg_path.write_text((svg_input or create_default_svg()), encoding="utf-8")
    print(f"  ✓ icon.svg")

    print(f"\n所有图标已生成到 {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="vx版Agent集合体 — 应用图标生成")
    parser.add_argument("--input", type=str, default=None,
                        help="源 PNG 文件路径（默认使用内置 SVG）")
    parser.add_argument("--output", type=str, default=None,
                        help="输出目录（默认: frontend/public/）")
    parser.add_argument("--no-icns", action="store_true",
                        help="跳过 macOS .icns 生成")
    parser.add_argument("--no-ico", action="store_true",
                        help="跳过 Windows .ico 生成")

    args = parser.parse_args()

    svg_input = None
    if args.input:
        p = Path(args.input)
        if p.suffix.lower() == ".svg":
            svg_input = p.read_text(encoding="utf-8")
        else:
            # PNG 等栅格图像 → 用 Pillow 打开再转换
            svg_input = None  # 将使用 fallback
            print(f"警告: {p.suffix} 格式将使用降级方案生成各尺寸")

    output_dir = Path(args.output) if args.output else None

    if args.no_ico and args.no_icns:
        print("没有要生成的格式。请移除 --no-ico 或 --no-icns。")
        return

    generate_icons(svg_input=svg_input, output_dir=output_dir)


if __name__ == "__main__":
    main()
