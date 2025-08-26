from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np


def detect_faces_bboxes_bgr(frame_bgr: "cv2.Mat") -> List[Tuple[int, int, int, int]]:
	gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
	cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
	# Slightly more permissive params
	rects = cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(48, 48))
	bboxes: List[Tuple[int, int, int, int]] = []
	for (x, y, w, h) in rects:
		top, left, bottom, right = y, x, y + h, x + w
		bboxes.append((top, right, bottom, left))
	return bboxes


def compute_face_embedding(frame_bgr: "cv2.Mat", bbox: Tuple[int, int, int, int]) -> np.ndarray:
	"""Return a simple embedding by resizing grayscale crop to 112x112 and flattening.
	This is a lightweight placeholder for demo purposes.
	"""
	top, right, bottom, left = bbox
	crop = frame_bgr[max(0, top):max(top + 1, bottom), max(0, left):max(left + 1, right)]
	if crop.size == 0:
		return np.zeros((112*112,), dtype=np.float32)
	gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
	resized = cv2.resize(gray, (112, 112), interpolation=cv2.INTER_AREA)
	norm = resized.astype(np.float32) / 255.0
	flat = norm.flatten()
	# L2 normalize
	n = np.linalg.norm(flat) + 1e-9
	return (flat / n).astype(np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
	a_n = a / (np.linalg.norm(a) + 1e-9)
	b_n = b / (np.linalg.norm(b) + 1e-9)
	return float(np.dot(a_n, b_n))


