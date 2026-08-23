import json
import os
import subprocess
import sys
import time

DOT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PY = os.path.join(DOT_DIR, "main.py")
CONFIG_PATH = os.path.join(DOT_DIR, "config.json")
PID_FILE = "/tmp/dot.pid"

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def get_interval():
    config = load_config()
    try:
        interval = float(
            config.get("settings", {}).get("startup_check_interval", 0.5)
        )
        return max(0.1, min(interval, 10.0))
    except (TypeError, ValueError):
        return 0.5

def is_dot_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE, "r") as f:
            pid = f.read().strip()
        if not pid.isdigit():
            return False
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, FileNotFoundError):
        return False
    except PermissionError:
        return True
    except OSError:
        return False

def start_dot():
    print("[STARTUP] Dot is not running. Starting Dot...")
    try:
        subprocess.Popen(
            [sys.executable, MAIN_PY],
            cwd=DOT_DIR,
            start_new_session=True
        )
    except Exception as e:
        print(f"[STARTUP] Failed to start Dot: {e}")

def main():
    print("[STARTUP] Dot startup watchdog started.")
    while True:
        config = load_config()
        auto_start = config.get("settings", {}).get("auto_start", False)
        if auto_start and not is_dot_running():
            start_dot()
        time.sleep(get_interval())

if __name__ == "__main__":
    main()
