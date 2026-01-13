from __future__ import annotations

import cv2
import numpy as np
from typing import Any

from mediapipe.python.solutions import face_mesh


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

OUTPUT_SIZE = 512
EYE_TARGET_Y = 0.35
EYE_DISTANCE_TARGET = 0.30 * OUTPUT_SIZE


# ---------------------------------------------------------
# MEDIAPIPE INITIALIZATION
# ---------------------------------------------------------

_face_mesh = face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7,
)


# ---------------------------------------------------------
# LANDMARK INDICES (MediaPipe)
# ---------------------------------------------------------

LEFT_EYE_IDX = [33, 133, 159, 145, 153, 154, 155, 173]
RIGHT_EYE_IDX = [362, 263, 386, 374, 380, 381, 382, 398]


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------


def _mean_point(landmarks, indices) -> np.ndarray:
    pts = np.array(
        [[landmarks[i].x, landmarks[i].y] for i in indices],
        dtype=np.float32,
    )
    return pts.mean(axis=0)


# ---------------------------------------------------------
# CORE ALIGNMENT
# ---------------------------------------------------------


def align_face(image_path: str) -> np.ndarray:
    """
    Align a face image to canonical position.

    Returns:
        aligned face as numpy ndarray (BGR, OUTPUT_SIZE x OUTPUT_SIZE)
    Raises:
        RuntimeError if no face detected
    """

    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Failed to read image: {image_path}")

    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 🔑 IMPORTANT FIX: cast to Any
    result: Any = _face_mesh.process(rgb)

    if result.multi_face_landmarks is None:
        raise RuntimeError("No face detected")

    landmarks = result.multi_face_landmarks[0].landmark

    left_eye = _mean_point(landmarks, LEFT_EYE_IDX)
    right_eye = _mean_point(landmarks, RIGHT_EYE_IDX)

    left_eye_px = np.array([left_eye[0] * w, left_eye[1] * h], dtype=np.float32)
    right_eye_px = np.array([right_eye[0] * w, right_eye[1] * h], dtype=np.float32)

    # Convert to pixel coords
    left_eye_px = np.array([left_eye[0] * w, left_eye[1] * h], dtype=np.float32)
    right_eye_px = np.array([right_eye[0] * w, right_eye[1] * h], dtype=np.float32)

    # Angle (degrees)
    dy = right_eye_px[1] - left_eye_px[1]
    dx = right_eye_px[0] - left_eye_px[0]
    angle = float(np.degrees(np.arctan2(dy, dx)))

    # Scale (IMPORTANT: cast to float)
    eye_dist = np.linalg.norm(right_eye_px - left_eye_px)
    if eye_dist <= 1.0:
        raise RuntimeError("Invalid eye distance")

    scale = float(EYE_DISTANCE_TARGET / eye_dist)

    # Centers
    eyes_center = (left_eye_px + right_eye_px) / 2.0
    target_center = np.array(
        [OUTPUT_SIZE / 2, OUTPUT_SIZE * EYE_TARGET_Y],
        dtype=np.float32,
    )

    # Rotation matrix
    M = cv2.getRotationMatrix2D(
        center=(float(eyes_center[0]), float(eyes_center[1])),
        angle=angle,
        scale=scale,
    )

    # Translate to target
    M[0, 2] += float(target_center[0] - eyes_center[0])
    M[1, 2] += float(target_center[1] - eyes_center[1])

    # Warp
    aligned = cv2.warpAffine(
        img,
        M,
        (OUTPUT_SIZE, OUTPUT_SIZE),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT,
    )

    return aligned
