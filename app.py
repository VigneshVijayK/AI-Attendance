from __future__ import annotations

import signal
import sys

import cv2

from camera import CameraManager, CameraSpec
from db import fetch_cameras, initialize_database, add_camera, update_camera
from face_engine import FaceRecognitionEngine


engine = FaceRecognitionEngine()
manager = CameraManager(on_frame=lambda cam_id, frame: engine.process_frame(cam_id, frame))


def _graceful_exit(*_: object) -> None:
	manager.stop_all()
	sys.exit(0)


def bootstrap() -> None:
	initialize_database()
	engine.load_known_faces()

	# Ensure a default laptop webcam (USB index 0) exists and is enabled if nothing else is enabled
	cams = fetch_cameras()
	enabled = [c for c in cams if str(c.status).lower() != "disabled"]
	if len(enabled) == 0:
		usb0 = next((c for c in cams if c.type == "usb" and str(c.rtsp_url) == "0"), None)
		if usb0 is None:
			add_camera(name="Default Laptop Webcam", type="usb", rtsp_url="0")
		else:
			update_camera(usb0.id, status="offline")  # re-enable if disabled

	# Reload and start only enabled cameras
	for c in fetch_cameras():
		if str(c.status).lower() == "disabled":
			continue
		source = c.rtsp_url if c.type in {"onvif", "rtsp"} else str(c.rtsp_url or "0")
		spec = CameraSpec(id=c.id, name=c.name, type=c.type, source=source)
		manager.upsert_camera(spec)

	print("App is running. Use Ctrl+C to stop.")
	signal.signal(signal.SIGINT, _graceful_exit)
	signal.signal(signal.SIGTERM, _graceful_exit)

	# Keep main thread alive
	try:
		while True:
			cv2.waitKey(250)
	except KeyboardInterrupt:
		_graceful_exit()


if __name__ == "__main__":
	bootstrap()

