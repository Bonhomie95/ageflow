from __future__ import annotations

import numpy as np
import math


def eye_tilt(left_eye, right_eye) -> float:
    dy = right_eye[1] - left_eye[1]
    dx = right_eye[0] - left_eye[0]
    return abs(math.degrees(math.atan2(dy, dx)))


def estimate_yaw(left_eye, right_eye, nose) -> float:
    eye_mid = (left_eye + right_eye) / 2
    dx = nose[0] - eye_mid[0]
    dy = nose[1] - eye_mid[1]
    return abs(math.degrees(math.atan2(dx, dy)))


def face_ratio(top, bottom, img_h) -> float:
    return abs(bottom[1] - top[1]) / img_h
