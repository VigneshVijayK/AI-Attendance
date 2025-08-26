from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import cv2

from config import FRAME_FPS, FRAME_HEIGHT, FRAME_WIDTH
from db import update_camera_status


FrameCallback = Callable[[int, "cv2.Mat"], None]


@dataclass
class CameraSpec:
	id: int
	name: str
	type: str  # "usb" | "onvif" | "rtsp"
	source: str  # index as str for usb (e.g., "0") or RTSP URL


class CameraWorker:
	def __init__(self, spec: CameraSpec, on_frame: FrameCallback) -> None:
		self.spec = spec
		self.on_frame = on_frame
		self._thread: Optional[threading.Thread] = None
		self._stop_event = threading.Event()
		self._capture: Optional[cv2.VideoCapture] = None

	def start(self) -> None:
		if self._thread and self._thread.is_alive():
			return
		self._stop_event.clear()
		self._thread = threading.Thread(target=self._run, name=f"Camera-{self.spec.id}", daemon=True)
		self._thread.start()

	def stop(self) -> None:
		self._stop_event.set()
		if self._thread:
			self._thread.join(timeout=2.0)
		if self._capture:
			try:
				self._capture.release()
			except Exception:
				pass
		try:
			update_camera_status(self.spec.id, "offline")
		except Exception:
			pass

	def _open_capture(self) -> Optional[cv2.VideoCapture]:
		cap: Optional[cv2.VideoCapture]
		if self.spec.type == "usb":
			index = int(self.spec.source)
			cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
			if cap and cap.isOpened():
				# Prefer MJPEG for smoother USB capture
				try:
					cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
					cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
				except Exception:
					pass
		else:
			cap = cv2.VideoCapture(self.spec.source)
		if not cap or not cap.isOpened():
			return None
		cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
		cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
		cap.set(cv2.CAP_PROP_FPS, FRAME_FPS)
		return cap

	def _run(self) -> None:
		frame_interval = 1.0 / max(1, FRAME_FPS)
		consecutive_failures = 0
		last_status_online = False
		while not self._stop_event.is_set():
			# Ensure capture is open
			if self._capture is None or not self._capture.isOpened():
				if self._capture is not None:
					try:
						self._capture.release()
					except Exception:
						pass
				self._capture = self._open_capture()
				if self._capture is None:
					if last_status_online:
						try:
							update_camera_status(self.spec.id, "offline")
						except Exception:
							pass
						last_status_online = False
					time.sleep(1.0)
					continue
				# Mark online when opened successfully
				if not last_status_online:
					try:
						update_camera_status(self.spec.id, "online")
					except Exception:
						pass
					last_status_online = True

			ok, frame = self._capture.read()
			if not ok or frame is None:
				consecutive_failures += 1
				# If too many failures, force reconnect
				if consecutive_failures >= 20:
					try:
						self._capture.release()
					except Exception:
						pass
					self._capture = None
					try:
						update_camera_status(self.spec.id, "offline")
					except Exception:
						pass
					last_status_online = False
					consecutive_failures = 0
					time.sleep(1.0)
					continue
				# small backoff on transient failure
				time.sleep(0.05)
				continue

			# success
			consecutive_failures = 0
			self.on_frame(self.spec.id, frame)
			time.sleep(frame_interval)


class CameraManager:
	def __init__(self, on_frame: FrameCallback) -> None:
		self.on_frame = on_frame
		self._workers: Dict[int, CameraWorker] = {}

	def upsert_camera(self, spec: CameraSpec) -> None:
		if spec.id in self._workers:
			self._workers[spec.id].stop()
		worker = CameraWorker(spec, self.on_frame)
		self._workers[spec.id] = worker
		worker.start()

	def stop_all(self) -> None:
		for worker in list(self._workers.values()):
			worker.stop()
		self._workers.clear()


