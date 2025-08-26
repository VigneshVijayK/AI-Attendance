import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).parent
PORT = int(os.environ.get("AI_ATTENDANCE_PORT", "8501"))
URL = f"http://127.0.0.1:{PORT}"
SENTINEL = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "AI_Attendance" / "browser_opened.txt"


def _is_port_in_use(port: int) -> bool:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.settimeout(0.5)
		return s.connect_ex(("127.0.0.1", port)) == 0


def _wait_until_up(timeout: float = 20.0) -> bool:
	start = time.time()
	while time.time() - start < timeout:
		try:
			with urlopen(URL, timeout=1.0) as _:
				return True
		except Exception:
			time.sleep(0.5)
	return False


def _open_browser_once() -> None:
	try:
		SENTINEL.parent.mkdir(parents=True, exist_ok=True)
		if not SENTINEL.exists():
			webbrowser.open_new(URL)
			try:
				SENTINEL.write_text(str(time.time()), encoding="utf-8")
			except Exception:
				pass
	except Exception:
		pass


def main() -> None:
	# Work in project root
	try:
		os.chdir(str(ROOT))
	except Exception:
		pass

	# Respect single instance: if port is in use, assume running → just open browser once and exit
	if _is_port_in_use(PORT):
		_open_browser_once()
		return

	# Headless environment to avoid Streamlit auto-opening browser
	env = os.environ.copy()
	env["STREAMLIT_SERVER_HEADLESS"] = "true"
	env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
	# Prefer consistent address/port
	args = [
		sys.executable,
		"-m",
		"streamlit",
		"run",
		"dashboard.py",
		"--server.headless",
		"true",
		"--server.address",
		"127.0.0.1",
		"--server.port",
		str(PORT),
		"--browser.gatherUsageStats",
		"false",
		"--server.runOnSave",
		"false",
		"--server.fileWatcherType",
		"none",
	]

	proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)

	# Wait for the server to come up, then open the browser once
	if _wait_until_up(timeout=25.0):
		_open_browser_once()

	# Stream logs
	if proc.stdout is not None:
		for line in iter(proc.stdout.readline, b""):
			if not line:
				break
			try:
				print(line.decode(errors="ignore"), end="")
			except Exception:
				pass

	proc.wait()


if __name__ == "__main__":
	main()

