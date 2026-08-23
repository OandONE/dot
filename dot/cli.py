import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
import glob
import json
import signal
import psutil

from core.config import load_config
from core.watcher import Watcher


def print_help():
    print("""
🟢 Dot - Privacy Indicator CLI

Usage: dot <command> [options]

Commands:
  start           Start Dot GUI
  status          Show current device status
  block <device>  Block a device (cam, mic)
  unblock <device> Unblock a device
  kill            Kill all apps using devices
  history         Show access history
  settings        Open Settings window
  install         Run install.sh
  uninstall       Remove Dot completely
  web             Open Web Panel
  help            Show this help
""")


def start_gui():
    subprocess.run([
        sys.executable,
        "/opt/dot/main.py"
    ])


def show_status():
    try:
        config = load_config()
        watcher = Watcher(config)
        watcher.check_all(notify=False)

        mic = watcher.active_devices.get("microphone")
        cam = watcher.active_devices.get("camera")
        scr = watcher.active_devices.get("screenshare")   # <-- جدید

        print(f"📷 Camera: {'🟢 Active' if cam else '⚪ Inactive'}")
        print(f"🎤 Microphone: {'🟢 Active' if mic else '⚪ Inactive'}")
        print(f"🖥️ Screenshare: {'🟢 Active' if scr else '⚪ Inactive'}")   # <-- جدید
    except Exception as e:
        print(f"Could not check status: {e}")


def _get_mic_tool():
    if shutil.which("wpctl"):
        return "wpctl"

    if shutil.which("pactl"):
        return "pactl"

    return None


def _mute_mic(mute=True):
    tool = _get_mic_tool()

    if tool == "wpctl":
        subprocess.run(
            [
                "wpctl",
                "set-mute",
                "@DEFAULT_AUDIO_SOURCE@",
                "1" if mute else "0"
            ],
            check=False
        )

    elif tool == "pactl":
        source = subprocess.run(
            ["pactl", "get-default-source"],
            capture_output=True,
            text=True,
            check=False
        ).stdout.strip()

        if source:
            subprocess.run(
                [
                    "pactl",
                    "set-source-mute",
                    source,
                    "1" if mute else "0"
                ],
                check=False
            )

    return tool

def block_device(device):
    if device in ("cam", "camera"):
        result = subprocess.run(["sudo", "modprobe", "-r", "uvcvideo"], capture_output=True, text=True)
        if result.returncode == 0:
            print("📷 Camera blocked")
        else:
            print(f"📷 Failed: {result.stderr.strip()}")
    elif device == "mic":
        tool = _mute_mic(True)
        print(f"🎤 Microphone blocked ({tool})")
    elif device == "screen":
        try:
            result = subprocess.run([
                "gdbus", "call",
                "--session",
                "--dest", "org.gnome.Shell.Screencast",
                "--object-path", "/org/gnome/Shell/Screencast",
                "--method", "org.gnome.Shell.Screencast.Stop"
            ], capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0:
                print("🖥️ Screenshare recording stopped successfully.")
            else:
                print("🖥️ Trying alternative method...")
                subprocess.run([
                    "xdotool", "key", "Ctrl+Alt+Shift+R"
                ], check=False)
                print("🖥️ Sent stop recording shortcut (Ctrl+Alt+Shift+R)")
        except Exception as e:
            print(f"🖥️ Could not stop screenshare: {e}")
            print("📌 Please stop screen sharing manually.")
    else:
        print("Usage: dot block <cam|mic|screen>")

def unblock_device(device):
    if device in ("cam", "camera"):
        result = subprocess.run(["sudo", "modprobe", "uvcvideo"], capture_output=True, text=True)
        if result.returncode == 0:
            print("📷 Camera unblocked")
        else:
            print(f"📷 Failed: {result.stderr.strip()}")
    elif device == "mic":
        tool = _mute_mic(False)
        print(f"🎤 Microphone unblocked ({tool})")
    elif device == "screen":
        print("🖥️ Screenshare unblocked (restart your sharing app if needed).")
    else:
        print("Usage: dot unblock <cam|mic|screen>")


def kill_all(device=None):
    if device in ["mic", "microphone", "audio"]:
        devices = glob.glob("/dev/snd/pcm*")
        for dev in devices:
            subprocess.run(["fuser", "-k", dev], check=False)
    elif device in ["cam", "camera", "webcam", "video"]:
        subprocess.run(["fuser", "-k", "/dev/video0"], check=False)
    elif device in ["screen", "screenshare", "share"]:
        subprocess.run(["pkill", "-f", "pipewire.*screen"], check=False)
        print("🖥️ Screenshare processes killed (if any)")
    else:
        # kill all
        subprocess.run(["fuser", "-k", "/dev/video0"], check=False)
        for dev in glob.glob("/dev/snd/pcm*"):
            subprocess.run(["fuser", "-k", dev], check=False)
        subprocess.run(["pkill", "-f", "pipewire.*screen"], check=False)
        print("☠️ All apps using devices killed")


def show_history():
    db_path = "/opt/dot/data/dot.db"

    if os.path.exists(db_path):
        subprocess.run([
            "sqlite3",
            "-header",
            "-column",
            db_path,
            """
            SELECT
                timestamp AS Time,
                device AS Device,
                process AS Process,
                duration AS Duration
            FROM access_log
            WHERE duration > 0
            ORDER BY timestamp DESC
            LIMIT 20;
            """
        ], check=False)
    else:
        print("No history yet")


def open_settings():
    subprocess.run([
        sys.executable,
        "/opt/dot/show_window.py",
        "settings"
    ])


def _flask_installed():
    try:
        import flask  # noqa: F401
        return True
    except ImportError:
        return False


def start_web():
    if not _flask_installed():
        print(
            "Flask is not installed.\n"
            "Please install Flask before using the Web Panel."
        )
        return

    def open_browser():
        time.sleep(1)
        webbrowser.open("http://localhost:8080")

    threading.Thread(
        target=open_browser,
        daemon=True
    ).start()

    subprocess.run([
        sys.executable,
        "/opt/dot/web/app.py"
    ])


def main():
    if len(sys.argv) < 2:
        print_help()
        return

    cmd = sys.argv[1]

    if cmd == "start":
        start_gui()

    elif cmd == "status":
        show_status()

    elif cmd == "block":
        device = sys.argv[2] if len(sys.argv) > 2 else None

        if device in ["cam", "camera"]:
            device = "cam"

        block_device(device)

    elif cmd == "unblock":
        device = sys.argv[2] if len(sys.argv) > 2 else None

        if device in ["cam", "camera"]:
            device = "cam"

        unblock_device(device)

    elif cmd == "kill":
        device = sys.argv[2] if len(sys.argv) > 2 else None
        kill_all(device)

    elif cmd == "history":
        show_history()

    elif cmd == "settings":
        open_settings()

    elif cmd == "install":
        subprocess.run([
            "bash",
            "/opt/dot/install.sh"
        ])

    elif cmd == "uninstall":
        print(
            "Run: sudo chattr -i "
            "/opt/dot/main.py /opt/dot/core/*.py "
            "&& sudo rm -rf /opt/dot"
        )

    elif cmd == "help":
        print_help()

    elif cmd == "web":
        start_web()

    else:
        print(f"Unknown command: {cmd}")
        print_help()


if __name__ == "__main__":
    main()
