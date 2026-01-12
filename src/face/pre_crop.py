from __future__ import annotations

import cv2
import numpy as np
from dlib import rectangle


def crop_face(img: np.ndarray, face: rectangle, expand: float = 0.6) -> np.ndarray:
    """
    Crop image around detected face and expand margins.
    """
    h, w = img.shape[:2]

    x1 = face.left()
    y1 = face.top()
    x2 = face.right()
    y2 = face.bottom()

    fw = x2 - x1
    fh = y2 - y1

    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2

    size = int(max(fw, fh) * (1 + expand))

    nx1 = max(0, cx - size // 2)
    ny1 = max(0, cy - size // 2)
    nx2 = min(w, cx + size // 2)
    ny2 = min(h, cy + size // 2)

    return img[ny1:ny2, nx1:nx2]
