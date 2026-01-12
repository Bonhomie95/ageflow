from __future__ import annotations

from pathlib import Path
import numpy as np
from dlib import shape_predictor

PREDICTOR_PATH = Path("models/shape_predictor_68_face_landmarks.dat")

if not PREDICTOR_PATH.exists():
    raise FileNotFoundError(
        "Missing shape_predictor_68_face_landmarks.dat in /models"
    )

_predictor = shape_predictor(str(PREDICTOR_PATH))


def get_landmarks(gray, face) -> np.ndarray:
    shape = _predictor(gray, face)
    coords = np.zeros((68, 2), dtype="float32")
    for i in range(68):
        coords[i] = (shape.part(i).x, shape.part(i).y)
    return coords
