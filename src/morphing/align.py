from __future__ import annotations

from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
import mediapipe as mp


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

OUTPUT_SIZE = 512
EYE_TARGET_Y = 0.35  # eyes vertical position in output
EYE_DISTANCE_TARGET = 0.30 * OUTPUT_SIZE  # normalized scale


# MediaPipe face mesh
_mp_face = mp.solutions.face_mesh.FaceMesh(
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
# CORE ALIGNMENT
# ---------------------------------------------------------


def _mean_point(landmarks, indices) -> np.ndarray:
    pts = np.array(
        [[landmarks[i].x, landmarks[i].y] for i in indices],
        dtype=np.float32,
    )
    return pts.mean(axis=0)


def align_face(image_path: str) -> np.ndarray:
    """
    Align a face image to canonical position.

    Returns:
        aligned face as numpy ndarray (BGR)
    Raises:
        RuntimeError if no face detected
    """

    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Failed to read image: {image_path}")

    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    res = _mp_face.process(rgb)
    if not res.multi_face_landmarks:
        raise RuntimeError("No face detected")

    landmarks = res.multi_face_landmarks[0].landmark

    # Eye centers (normalized coords)
    left_eye = _mean_point(landmarks, LEFT_EYE_IDX)
    right_eye = _mean_point(landmarks, RIGHT_EYE_IDX)

    # Convert to pixel coords
    left_eye_px = np.array([left_eye[0] * w, left_eye[1] * h])
    right_eye_px = np.array([right_eye[0] * w, right_eye[1] * h])

    # Compute angle
    dy = right_eye_px[1] - left_eye_px[1]
    dx = right_eye_px[0] - left_eye_px[0]
    angle = np.degrees(np.arctan2(dy, dx))

    # Compute scale
    eye_dist = np.linalg.norm(right_eye_px - left_eye_px)
    scale = EYE_DISTANCE_TARGET / eye_dist

    # Desired eye center position
    eyes_center = (left_eye_px + right_eye_px) / 2
    target_center = np.array(
        [
            OUTPUT_SIZE / 2,
            OUTPUT_SIZE * EYE_TARGET_Y,
        ]
    )

    # Rotation matrix
    M = cv2.getRotationMatrix2D(
        center=tuple(eyes_center),
        angle=angle,
        scale=scale,
    )

    # Shift to target center
    M[0, 2] += target_center[0] - eyes_center[0]
    M[1, 2] += target_center[1] - eyes_center[1]

    # Warp
    aligned = cv2.warpAffine(
        img,
        M,
        (OUTPUT_SIZE, OUTPUT_SIZE),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT,
    )

    return aligned
