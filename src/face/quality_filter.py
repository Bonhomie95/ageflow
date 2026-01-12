from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from .detector import detect_single_face
from .landmarks import get_landmarks
from .geometry import eye_tilt, estimate_yaw, face_ratio
from .align import align_face


class FaceQualityResult:
    def __init__(self, ok: bool, reason: str = ""):
        self.ok = ok
        self.reason = reason


class FaceQualityFilter:
    def __init__(
        self,
        max_yaw: float = 15.0,
        max_eye_tilt: float = 8.0,
        min_face_ratio: float = 0.40,
        max_face_ratio: float = 0.75,
    ):
        self.max_yaw = max_yaw
        self.max_eye_tilt = max_eye_tilt
        self.min_face_ratio = min_face_ratio
        self.max_face_ratio = max_face_ratio

    def check(self, image_path: Path) -> Tuple[FaceQualityResult, Optional[np.ndarray]]:
        img = cv2.imread(str(image_path))
        if img is None:
            return FaceQualityResult(False, "Unreadable image"), None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        face = detect_single_face(gray)
        if face is None:
            return FaceQualityResult(False, "No face or multiple faces"), None

        lm = get_landmarks(gray, face)

        left_eye = lm[36]
        right_eye = lm[45]
        nose = lm[30]
        top = lm[27]
        bottom = lm[8]

        ratio = face_ratio(top, bottom, h)
        if not (self.min_face_ratio <= ratio <= self.max_face_ratio):
            return FaceQualityResult(False, f"Bad face ratio {ratio:.2f}"), None

        yaw = estimate_yaw(left_eye, right_eye, nose)
        if yaw > self.max_yaw:
            return FaceQualityResult(False, f"Yaw too large {yaw:.1f}°"), None

        tilt = eye_tilt(left_eye, right_eye)
        if tilt > self.max_eye_tilt:
            return FaceQualityResult(False, f"Eye tilt {tilt:.1f}°"), None

        mouth_open = np.linalg.norm(lm[62] - lm[66])
        face_height = np.linalg.norm(top - bottom)

        if mouth_open > face_height * 0.15:
            return FaceQualityResult(False, "Mouth too open"), None

        aligned = align_face(img, left_eye, right_eye)
        return FaceQualityResult(True), aligned
