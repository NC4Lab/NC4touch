#!/usr/bin/env python3
"""Generate a perfect circular 'O' stimulus on a black background.

Default output matches NC4Touch display assets:
- Canvas: 320x480
- Circle diameter: 288 px
- White ring on black background
"""

from __future__ import annotations

import argparse
import os
from PIL import Image, ImageDraw


def generate_perfect_o(
    output_path: str,
    canvas_w: int = 320,
    canvas_h: int = 480,
    diameter: int = 288,
    ring_width: int = 60,
    color: tuple[int, int, int] = (255, 255, 255),
    bg: tuple[int, int, int] = (0, 0, 0),
) -> None:
    img = Image.new("RGB", (canvas_w, canvas_h), bg)
    draw = ImageDraw.Draw(img)

    cx = canvas_w // 2
    cy = canvas_h // 2
    radius = diameter // 2

    left = cx - radius
    top = cy - radius
    right = cx + radius
    bottom = cy + radius

    draw.ellipse((left, top, right, bottom), outline=color, width=ring_width)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate perfect circular O stimulus")
    parser.add_argument("--output", default="data/images/o.bmp", help="Output image path")
    parser.add_argument("--canvas-width", type=int, default=320)
    parser.add_argument("--canvas-height", type=int, default=480)
    parser.add_argument("--diameter", type=int, default=288)
    parser.add_argument("--ring-width", type=int, default=60)
    parser.add_argument("--backup", action="store_true", help="Backup existing output first")
    parser.add_argument("--backup-suffix", default=".pre_circle", help="Backup suffix before extension")

    args = parser.parse_args()

    if args.backup and os.path.exists(args.output):
        root, ext = os.path.splitext(args.output)
        backup_path = f"{root}{args.backup_suffix}{ext}"
        if not os.path.exists(backup_path):
            Image.open(args.output).save(backup_path)
            print(f"Backup saved: {backup_path}")
        else:
            print(f"Backup exists: {backup_path}")

    generate_perfect_o(
        output_path=args.output,
        canvas_w=args.canvas_width,
        canvas_h=args.canvas_height,
        diameter=args.diameter,
        ring_width=args.ring_width,
    )

    print(f"Generated perfect O: {args.output}")


if __name__ == "__main__":
    main()
