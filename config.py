from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOTS_DIR = DATA_DIR / "unknown_snapshots"
DB_PATH = DATA_DIR / "attendance.db"

# Create folders if missing
DATA_DIR.mkdir(exist_ok=True)
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Recognition thresholds
FACE_DISTANCE_THRESHOLD = 0.5  # lower = stricter
ABSENCE_MINUTES_FOR_CHECKOUT = 10

# Camera defaults
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_FPS = 15

# Dashboard
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 8501

# Misc
RANDOM_SEED = 42





