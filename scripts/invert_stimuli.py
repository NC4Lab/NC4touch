#!/usr/bin/env python3
"""Invert stimulus images (white <-> black) for one or more files.

Examples:
  python scripts/invert_stimuli.py data/images/o.bmp data/images/x.bmp --in-place
  python scripts/invert_stimuli.py data/images/o.bmp --output-dir data/images
"""

from __future__ import annotations

import argparse
import os
from PIL import Image, ImageOps


def invert_image(image_path: str, output_path: str, in_place: bool, backup_suffix: str) -> str:
    img = Image.open(image_path).convert("RGB")

    if in_place:
        root, ext = os.path.splitext(image_path)
        backup_path = f"{root}{backup_suffix}{ext}"
        if not os.path.exists(backup_path):
            img.save(backup_path)

    inverted = ImageOps.invert(img)
    inverted.save(output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Invert stimulus image colors")
    parser.add_argument("images", nargs="+", help="Input image paths")
    parser.add_argument("--in-place", action="store_true", help="Overwrite input images")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for outputs when not using --in-place",
    )
    parser.add_argument(
        "--suffix",
        default="_inverted",
        help="Output filename suffix when not using --in-place (default: _inverted)",
    )
    parser.add_argument(
        "--backup-suffix",
        default=".pre_invert",
        help="Backup suffix before extension when using --in-place",
    )

    args = parser.parse_args()

    for image_path in args.images:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        if args.in_place:
            output_path = image_path
        else:
            base_dir = args.output_dir if args.output_dir else os.path.dirname(image_path)
            base_name = os.path.basename(image_path)
            root, ext = os.path.splitext(base_name)
            output_path = os.path.join(base_dir, f"{root}{args.suffix}{ext}")

        saved = invert_image(
            image_path=image_path,
            output_path=output_path,
            in_place=args.in_place,
            backup_suffix=args.backup_suffix,
        )
        print(f"Saved: {saved}")


if __name__ == "__main__":
    main()
