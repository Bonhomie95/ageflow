from __future__ import annotations

from pathlib import Path
import shutil
import sys

import cv2
import numpy as np

from src.face.quality_filter import FaceQualityFilter


INPUT_DIR = Path("images/raw")
ACCEPTED_DIR = Path("faces/accepted")
REJECTED_DIR = Path("faces/rejected")


def main() -> None:
    print("🔍 Face filter starting...")
    print(f"📂 INPUT_DIR = {INPUT_DIR.resolve()}")

    if not INPUT_DIR.exists():
        print("❌ images/raw directory does NOT exist")
        sys.exit(1)

    face_filter = FaceQualityFilter()

    total_images = 0
    accepted = 0
    rejected = 0

    for celeb_dir in INPUT_DIR.iterdir():
        if not celeb_dir.is_dir():
            continue

        print(f"\n👤 Processing celebrity folder: {celeb_dir.name}")

        images = list(celeb_dir.iterdir())
        if not images:
            print("⚠️  No images found in this folder")
            continue

        for img_path in images:
            if not img_path.is_file():
                continue

            total_images += 1

            result, aligned = face_filter.check(img_path)

            if result.ok:
                if aligned is None:
                    print(f"SKIPPED {img_path.name}: aligned image missing")
                    continue

                out_dir = ACCEPTED_DIR / celeb_dir.name
                out_dir.mkdir(parents=True, exist_ok=True)

                out_img = out_dir / img_path.name
                cv2.imwrite(str(out_img), aligned)

                accepted += 1
                print(f"✅ ACCEPTED {img_path.name}")

            else:
                out_dir = REJECTED_DIR / celeb_dir.name
                out_dir.mkdir(parents=True, exist_ok=True)

                shutil.copy(img_path, out_dir / img_path.name)
                rejected += 1
                print(f"❌ REJECTED {img_path.name}: {result.reason}")

    print("\n📊 SUMMARY")
    print(f"Total images: {total_images}")
    print(f"Accepted: {accepted}")
    print(f"Rejected: {rejected}")
    print("✅ Face filtering complete")


if __name__ == "__main__":
    main()
