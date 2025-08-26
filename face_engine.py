from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from config import ABSENCE_MINUTES_FOR_CHECKOUT, FACE_DISTANCE_THRESHOLD, SNAPSHOTS_DIR
from db import Employee, fetch_employees, log_unknown, set_attendance_check_out, upsert_attendance_check_in
from face_utils import compute_face_embedding, cosine_similarity, detect_faces_bboxes_bgr


@dataclass
class MatchResult:
	employee_id: Optional[int]
	employee_name: Optional[str]
	face_location: Tuple[int, int, int, int]
	distance: Optional[float]


class FaceRecognitionEngine:
	def __init__(self) -> None:
		self._known_encodings: List[np.ndarray] = []
		self._known_ids: List[int] = []
		self._known_names: List[str] = []
		self._last_seen_at: Dict[int, datetime] = {}
		self._last_loaded_at: Optional[datetime] = None

	def load_known_faces(self) -> None:
		employees: List[Employee] = fetch_employees()
		self._known_encodings = [np.array(e.face_encoding, dtype=np.float32) for e in employees]
		self._known_ids = [e.id for e in employees]
		self._known_names = [e.name for e in employees]
		self._last_loaded_at = datetime.now()

	def _reload_if_stale(self) -> None:
		if self._last_loaded_at is None or (datetime.now() - self._last_loaded_at) > timedelta(seconds=30):
			self.load_known_faces()

	def process_frame(self, camera_id: int, frame: "cv2.Mat") -> List[MatchResult]:
		self._reload_if_stale()
		boxes = detect_faces_bboxes_bgr(frame)
		results: List[MatchResult] = []
		now = datetime.now()

		if len(boxes) == 0:
			self._handle_absences(now)
			return results

		for loc in boxes:
			emb = compute_face_embedding(frame, loc)
			match: Optional[MatchResult] = self._match_embedding(emb, loc)
			if match and match.employee_id is not None:
				upsert_attendance_check_in(match.employee_id, now)
				self._last_seen_at[match.employee_id] = now
				try:
					print(f"Matched: {match.employee_name} (id={match.employee_id})")
				except Exception:
					pass
			else:
				self._save_unknown_snapshot(frame, loc, now)
			results.append(match if match else MatchResult(None, None, loc, None))

		self._handle_absences(now)
		return results

	def _match_embedding(self, emb: np.ndarray, loc: Tuple[int, int, int, int]) -> Optional[MatchResult]:
		if not self._known_encodings:
			return None
		compatible: List[int] = [i for i, e in enumerate(self._known_encodings) if getattr(e, 'shape', None) == emb.shape]
		if not compatible:
			return None
		sims: List[float] = []
		for i in compatible:
			try:
				sims.append(cosine_similarity(self._known_encodings[i], emb))
			except Exception:
				sims.append(-1.0)
		best_local_index = int(np.argmax(sims))
		best_index = compatible[best_local_index]
		best_sim = float(sims[best_local_index])
		SIM_THRESHOLD = 0.6
		if best_sim >= SIM_THRESHOLD:
			return MatchResult(
				employee_id=self._known_ids[best_index],
				employee_name=self._known_names[best_index],
				face_location=loc,
				distance=1.0 - best_sim,
			)
		return None

	def _handle_absences(self, now: datetime) -> None:
		timeout = timedelta(minutes=ABSENCE_MINUTES_FOR_CHECKOUT)
		to_checkout: List[int] = []
		for emp_id, last_seen in list(self._last_seen_at.items()):
			if now - last_seen >= timeout:
				to_checkout.append(emp_id)
		for emp_id in to_checkout:
			set_attendance_check_out(emp_id, now)
			self._last_seen_at.pop(emp_id, None)

	def _save_unknown_snapshot(self, frame: "cv2.Mat", loc: Tuple[int, int, int, int], now: datetime) -> None:
		top, right, bottom, left = loc
		face_img = frame[max(0, top):max(top + 1, bottom), max(0, left):max(left + 1, right)]
		ts = now.strftime("%Y%m%d_%H%M%S_%f")
		path = SNAPSHOTS_DIR / f"unknown_{ts}.jpg"
		try:
			cv2.imwrite(str(path), face_img)
			log_unknown(str(path), now)
		except Exception:
			pass
