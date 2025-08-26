from __future__ import annotations

from pathlib import Path

import numpy as np

from db import add_camera, add_employee, initialize_database


def main() -> None:
	initialize_database()
	# Add a sample USB camera at index 0
	try:
		add_camera(name="USB Cam 0", type="usb", rtsp_url="0")
	except Exception:
		pass

	# Add placeholder employee with zero vector (replace via dashboard upload later)
	try:
		add_employee("Sample Employee", [0.0] * 128)
	except Exception:
		pass

	print("Seed complete.")


if __name__ == "__main__":
	main()





