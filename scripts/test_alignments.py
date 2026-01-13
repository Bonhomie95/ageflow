from pathlib import Path
import cv2

from src.morphing.align import align_face

img_path = "faces/accepted/leonardo-dicaprio/044_filedicapriocrawfordschwarzeneggerbyluiginovijpg.jpg"

aligned = align_face(img_path)
cv2.imshow("aligned", aligned)
cv2.waitKey(0)
cv2.destroyAllWindows()
