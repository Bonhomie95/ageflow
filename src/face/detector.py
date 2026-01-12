from __future__ import annotations

import numpy as np
from dlib import get_frontal_face_detector
_detector = get_frontal_face_detector()



def detect_single_face(gray: np.ndarray):
    faces = _detector(gray, 1)
    if len(faces) != 1:
        return None
    return faces[0]
