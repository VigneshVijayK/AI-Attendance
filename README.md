# Face Recognition Attendance System (Starter Scaffold)

This is a scaffold for a real-time attendance system using face recognition with support for both ONVIF CCTV (RTSP) and USB webcams.

## Structure

- `app_launcher.py` — Windows-friendly launcher (opens dashboard in browser)
- `app.py` — entrypoint to start camera workers (optional)
- `db.py` — database setup and CRUD helpers
- `camera.py` — camera workers (USB/RTSP) and manager
- `face_engine.py` — face recognition engine and attendance logic
- `dashboard.py` — Streamlit admin dashboard
- `config.py` — configuration values
- `requirements.txt` — Python dependencies
- `pyinstaller.spec` — build config for Windows EXE

## Quick start (dev)

1. Create a virtual environment and install deps

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Initialize database

```bash
python -c "import db; db.initialize_database()"
```

3. Run the dashboard

```bash
streamlit run dashboard.py
```

Or use the launcher:

```bash
python app_launcher.py
```

## Windows packaging (EXE)

1. Install PyInstaller

```bash
pip install pyinstaller
```

2. Build EXE

```bash
pyinstaller --clean pyinstaller.spec
```

3. Run

- Output at `dist/AI-Attendance.exe`
- Double-click to launch (opens `http://localhost:8501`)

Notes:
- Ensure the `data/` directory exists and is writable.
- If antivirus blocks the EXE, add it to allowed apps.
