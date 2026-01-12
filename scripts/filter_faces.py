from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np


# ------------------------------------------------------------------
# CONFIG (MORPH-FRIENDLY)
# ------------------------------------------------------------------

MIN_FACE_RATIO = 0.18      # % of image occupied by face
MIN_FACE_SIZE = 120        # px
OUTPUT_SIZE = 512          # aligned output size


# ------------------------------------------------------------------
# RESULT OBJECT
# ------------------------------------------------------------------

@dataclass
class FaceCheckResult:
    ok: bool
    reason: str = ""


# ------------------------------------------------------------------
# FACE QUALITY FILTER
# ------------------------------------------------------------------

class FaceQualityFilter:
    def __init__(self) -> None:
        cascade_path = Path(__file__).parent / "assets" / "haarcascade_frontalface_default.xml"

        if not cascade_path.exists():
            raise RuntimeError(
                f"Haar cascade not found at {cascade_path}. "
                f"Download haarcascade_frontalface_default.xml and place it there."
            )

        self.face_cascade = cv2.CascadeClassifier(str(cascade_path))

        if self.face_cascade.empty():
            raise RuntimeError("Failed to load Haar cascade (file corrupted or invalid).")

    # --------------------------------------------------------------
    # MAIN ENTRY
    # --------------------------------------------------------------

    def check(self, image_path: Path) -> Tuple[FaceCheckResult, Optional[np.ndarray]]:
        img = cv2.imread(str(image_path))

        if img is None:
            return FaceCheckResult(False, "Unreadable image"), None

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE),
        )

        if len(faces) == 0:
            return FaceCheckResult(False, "No face detected"), None

        # Pick dominant face (largest area)
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])

        face_area = fw * fh
        img_area = w * h
        face_ratio = face_area / img_area

        if face_ratio < MIN_FACE_RATIO:
            return (
                FaceCheckResult(False, f"Face too small (ratio {face_ratio:.2f})"),
                None,
            )

        aligned = self._align_and_crop(img, x, y, fw, fh)

        if aligned is None:
            return FaceCheckResult(False, "Alignment failed"), None

        return FaceCheckResult(True), aligned

    # --------------------------------------------------------------
    # ALIGNMENT
    # --------------------------------------------------------------

    def _align_and_crop(
        self, img: np.ndarray, x: int, y: int, w: int, h: int
    ) -> Optional[np.ndarray]:
        img_h, img_w = img.shape[:2]

        pad = int(0.25 * max(w, h))
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img_w, x + w + pad)
        y2 = min(img_h, y + h + pad)

        crop = img[y1:y2, x1:x2]

        if crop.size == 0:
            return None

        return cv2.resize(crop, (OUTPUT_SIZE, OUTPUT_SIZE))
