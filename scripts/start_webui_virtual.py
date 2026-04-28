"""Launch the WebUI against the virtual chamber backend."""

import os
import sys
import tempfile
from pathlib import Path

# Set env vars FIRST before any imports
os.environ.setdefault("NC4TOUCH_VIRTUAL_MODE", "1")

# Create temp directories for virtual testing (especially important on macOS)
if not os.path.exists("/mnt/shared"):
    temp_data_dir = os.path.join(tempfile.gettempdir(), "nc4touch_data")
    temp_video_dir = os.path.join(tempfile.gettempdir(), "nc4touch_videos")
    os.makedirs(temp_data_dir, exist_ok=True)
    os.makedirs(temp_video_dir, exist_ok=True)
    os.environ["NC4TOUCH_DATA_DIR"] = temp_data_dir
    os.environ["NC4TOUCH_VIDEO_DIR"] = temp_video_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CONTROLLER_DIR = REPO_ROOT / "Controller"
if str(CONTROLLER_DIR) not in sys.path:
    sys.path.insert(0, str(CONTROLLER_DIR))

from WebUI import setup_webui  # noqa: E402

# Set up the WebUI after env vars are configured
setup_webui()
