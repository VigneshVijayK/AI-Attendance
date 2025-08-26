from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List, Optional

import pandas as pd
import streamlit as st

from config import SNAPSHOTS_DIR
from db import (
	add_camera,
	add_employee,
	add_attendance,
	connect_db,
	delete_attendance,
	delete_employee,
	export_attendance_to_excel,
	export_attendance_to_csv,
	export_unknowns_to_excel,
	fetch_cameras,
	fetch_employees,
	fetch_unknowns,
	update_camera,
	delete_camera,
	delete_unknown,
)
from onvif_helper import discover_onvif_devices, build_rtsp_from_onvif
from face_engine import FaceRecognitionEngine

st.set_page_config(page_title="AI Attendance", layout="wide")

# --------------------- Engine cache ---------------------

def _get_engine() -> FaceRecognitionEngine:
	eng: Optional[FaceRecognitionEngine] = st.session_state.get("_engine")  # type: ignore
	if eng is None:
		eng = FaceRecognitionEngine()
		eng.load_known_faces()
		st.session_state["_engine"] = eng
	return eng  # type: ignore

# --------------------- Background detection runner ---------------------

class DetectionRunner:
	def __init__(self) -> None:
		self._thread = None
		self._stop = False
		self._source: Optional[str] = None

	def start(self, source: str) -> None:
		import threading
		self.stop()
		self._stop = False
		self._source = source
		self._thread = threading.Thread(target=self._run, name="DetectionRunner", daemon=True)
		self._thread.start()

	def stop(self) -> None:
		self._stop = True
		thr = self._thread
		self._thread = None
		if thr and thr.is_alive():
			try:
				thr.join(timeout=0.2)
			except Exception:
				pass

	def _run(self) -> None:
		import cv2, time
		engine = _get_engine()
		src = self._source or "0"
		cap = None
		try:
			cap = cv2.VideoCapture(int(src)) if src.isdigit() else cv2.VideoCapture(src)
			if not cap or not cap.isOpened():
				return
			while not self._stop:
				ok, frame = cap.read()
				if not ok:
					time.sleep(0.05)
					continue
				engine.process_frame(camera_id=-400, frame=frame)
				time.sleep(0.05)
		finally:
			try:
				if cap and cap.isOpened():
					cap.release()
			except Exception:
				pass

# singleton in session state
if "_detector" not in st.session_state:
	st.session_state["_detector"] = DetectionRunner()

# --------------------- Cameras Tab ---------------------

def cameras_tab() -> None:
	st.header("Cameras")
	cams = fetch_cameras()

	# Source selector for background detection
	sources: List[str] = []
	for c in cams:
		if c.rtsp_url:
			sources.append(c.rtsp_url)
	for i in range(0, 6):
		val = str(i)
		if val not in sources:
			sources.append(val)
	selected_source = st.selectbox("Detection source (background)", options=sources)
	st.session_state["selected_source"] = selected_source

	# Program controls -> start/stop only the background detector
	c1, c2 = st.columns([1,1])
	with c1:
		if st.button("Start Program (detection)"):
			st.session_state["detect_on"] = True
			st.session_state["_detector"].start(selected_source)
	with c2:
		if st.button("Stop Program (detection)"):
			st.session_state["detect_on"] = False
			st.session_state["_detector"].stop()
	st.caption("Detection runs in background using OpenCV; no frames rendered.")

	# Smooth preview (optional, browser camera)
	st.subheader("Preview (browser camera)")
	try:
		from streamlit_webrtc import webrtc_streamer, WebRtcMode
		import av
		class Processor:
			def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
				img = frame.to_ndarray(format="bgr24")
				return av.VideoFrame.from_ndarray(img, format="bgr24")
		webrtc_streamer(key="webrtc", mode=WebRtcMode.SENDRECV, media_stream_constraints={"video": True, "audio": False}, video_processor_factory=Processor)
	except Exception:
		st.info("Install streamlit-webrtc for smooth preview or ignore this section.")

	st.subheader("Configured Cameras")
	for cam in cams:
		with st.container(border=True):
			c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
			with c1:
				st.write(f"[{cam.id}] {cam.name} ({cam.type})")
				st.caption(f"Source: {cam.rtsp_url}")
			with c2:
				st.write(f"Status: {cam.status}")
			with c3:
				if st.button("Enable", key=f"en_{cam.id}"):
					update_camera(cam.id, status="offline")
					st.rerun()
			with c4:
				if st.button("Disable", key=f"dis_{cam.id}"):
					update_camera(cam.id, status="disabled")
					st.rerun()


def employees_tab() -> None:
	st.header("Employees")
	with st.expander("Enroll Employee (upload one face image)"):
		with st.form("enroll_form", clear_on_submit=True):
			name = st.text_input("Name")
			image = st.file_uploader("Face Image", type=["jpg", "jpeg", "png"])
			submitted = st.form_submit_button("Enroll")
			if submitted and name and image is not None:
				import numpy as np
				import cv2
				from face_utils import detect_faces_bboxes_bgr, compute_face_embedding

				file_bytes = image.read()
				img_array = np.frombuffer(file_bytes, dtype=np.uint8)
				bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
				boxes = detect_faces_bboxes_bgr(bgr)
				if len(boxes) == 0:
					st.error("No face detected in image")
				else:
					enc = compute_face_embedding(bgr, boxes[0]).astype(float).tolist()
					add_employee(name, enc)
					_get_engine().load_known_faces()
					st.success(f"Enrolled {name}")

	emps = fetch_employees()
	st.subheader("Registered Employees")
	df = pd.DataFrame([{"id": e.id, "name": e.name} for e in emps])
	st.dataframe(df, use_container_width=True)

	col1, col2 = st.columns([2,1])
	with col1:
		if st.button("Reload faces now"):
			_get_engine().load_known_faces()
			st.success("Faces reloaded")
	with col2:
		emp_to_del = st.text_input("Delete employee ID")
		if st.button("Delete Employee") and emp_to_del.isdigit():
			delete_employee(int(emp_to_del))
			_get_engine().load_known_faces()
			st.success("Employee deleted")
			st.rerun()


def attendance_tab() -> None:
	st.header("Attendance")
	name_filter = st.text_input("Filter by name contains")
	date_filter = st.date_input("Date", value=date.today())

	with connect_db() as conn:
		df = pd.read_sql_query(
			"""
			SELECT a.id, e.id as emp_id, e.name as employee, a.date, a.in_time, a.out_time, a.status
			FROM attendance a INNER JOIN employees e ON a.emp_id = e.id
			WHERE date = ?
			ORDER BY a.in_time ASC
			""",
			conn,
			params=(date_filter.isoformat(),),
		)
	if name_filter:
		df = df[df["employee"].str.contains(name_filter, case=False, na=False)]
	st.dataframe(df, use_container_width=True)

	st.subheader("Add attendance entry")
	with st.form("add_attendance_form", clear_on_submit=True):
		emp = st.selectbox("Employee", options=[(e.id, e.name) for e in fetch_employees()], format_func=lambda x: x[1])
		in_time = st.text_input("IN time (HH:MM:SS)")
		out_time = st.text_input("OUT time (HH:MM:SS)")
		status = st.selectbox("Status", ["present", "absent", "manual"]) 
		sub = st.form_submit_button("Add")
		if sub:
			add_attendance(emp[0], date_filter.isoformat(), in_time or None, out_time or None, status)
			st.success("Added")
			st.rerun()

	st.subheader("Delete attendance entry")
	del_id = st.text_input("Attendance ID to delete")
	if st.button("Delete") and del_id.isdigit():
		delete_attendance(int(del_id))
		st.success("Deleted")
		st.rerun()

	col1, col2 = st.columns(2)
	with col1:
		if st.button("Export CSV"):
			path = Path("reports/attendance.csv")
			export_attendance_to_csv(path)
			st.success(f"Exported to {path}")
	with col2:
		if st.button("Export Excel"):
			path = Path("reports/attendance.xlsx")
			export_attendance_to_excel(path)
			st.success(f"Exported to {path}")


def unknowns_tab() -> None:
	st.header("Unknown Detections")
	rows = fetch_unknowns()
	if rows:
		st.dataframe(pd.DataFrame(rows), use_container_width=True)
		uid = st.text_input("Unknown ID to delete")
		if st.button("Delete Unknown") and uid.isdigit():
			delete_unknown(int(uid))
			st.success("Deleted")
			st.rerun()
	else:
		st.info("No unknowns yet.")

	col1, col2 = st.columns(2)
	with col1:
		if st.button("Export Unknowns Excel"):
			path = Path("reports/unknowns.xlsx")
			export_unknowns_to_excel(path)
			st.success(f"Exported to {path}")
	with col2:
		st.caption("Use Employees tab to enroll an unknown face into employees.")


def reports_tab() -> None:
	st.header("Reports")
	st.write("Use the Attendance tab to export CSV/Excel. Add scheduled jobs here later.")


def main() -> None:
	tabs = st.tabs(["Cameras", "Employees", "Attendance", "Unknown", "Reports"])
	with tabs[0]:
		cameras_tab()
	with tabs[1]:
		employees_tab()
	with tabs[2]:
		attendance_tab()
	with tabs[3]:
		unknowns_tab()
	with tabs[4]:
		reports_tab()


if __name__ == "__main__":
	main()
