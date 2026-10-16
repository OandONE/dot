import json
import os
import subprocess
import time


BASE_DIR = "/opt/dot"
MAIN_PY = os.path.join(BASE_DIR, "main.py")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PYTHON = os.path.join(BASE_DIR, ".venv", "bin", "python3")


def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WATCHDOG] Config error: {e}", flush=True)
        return {}

def update_environment_from_session():
    try:
        output = subprocess.check_output(
            ["systemctl", "--user", "show-environment"],
            text=True
        )
        for line in output.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in (
                "DISPLAY",
                "WAYLAND_DISPLAY",
                "XDG_RUNTIME_DIR",
                "XDG_CURRENT_DESKTOP",
                "XDG_SESSION_DESKTOP",
                "DESKTOP_SESSION",
            ):
                if key not in os.environ or not os.environ[key]:
                    os.environ[key] = value
    except Exception as e:
        print(f"[WATCHDOG] Could not update environment: {e}", flush=True)

def get_interval():
    config = load_config()

    try:
        interval = float(
            config.get("settings", {}).get(
                "startup_check_interval",
                0.5
            )
        )

        return max(0.1, min(interval, 5.0))

    except (TypeError, ValueError):
        return 0.5


def is_dot_running():
    try:
        result = subprocess.run(
            ["pgrep", "-f", "/opt/dot/main.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return result.returncode == 0

    except Exception:
        return False


def graphical_session_ready():
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"):
        return True

    update_environment_from_session()
    return bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))


def start_dot():
    try:
        print("[WATCHDOG] Starting Dot...", flush=True)

        subprocess.Popen(
            [PYTHON, MAIN_PY],
            cwd=BASE_DIR,
            start_new_session=True
        )

    except Exception as e:
        print(
            f"[WATCHDOG] Failed to start Dot: {e}",
            flush=True
        )


def main():
    update_environment_from_session()

    print(
        "[WATCHDOG] Dot startup watchdog started.",
        flush=True
    )

    while True:

        config = load_config()

        auto_start = (
            config
            .get("settings", {})
            .get("auto_start", False)
        )

        # Startup is disabled.
        # Do not start Dot.
        if not auto_start:
            time.sleep(get_interval())
            continue

        # Wait for graphical session.
        if not graphical_session_ready():
            print(
                "[WATCHDOG] Waiting for graphical session...",
                flush=True
            )

            time.sleep(get_interval())
            continue

        # Dot is already running.
        if is_dot_running():
            time.sleep(get_interval())
            continue

        # Startup is enabled but Dot isn't running.
        start_dot()

        time.sleep(get_interval())


if __name__ == "__main__":
    main()
