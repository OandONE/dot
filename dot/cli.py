import sys
import os
import subprocess
import glob
import threading
import webbrowser
import time
import shutil

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
  help            Show this help
""")

def start_gui():
    subprocess.run(['python3', '/opt/dot/main.py'])

def show_status():
    try:
        result = subprocess.run(['fuser', '/dev/video0'], capture_output=True, text=True)
        cam = result.stdout.strip() if result.stdout else "inactive"
        
        result = subprocess.run(['fuser', '/dev/snd/pcmC0D0c'], capture_output=True, text=True)
        mic = result.stdout.strip() if result.stdout else "inactive"
        
        print(f"📷 Camera: {'🟢 Active' if cam else '⚪ Inactive'}")
        print(f"🎤 Microphone: {'🟢 Active' if mic else '⚪ Inactive'}")
    except:
        print("Could not check status")


def _get_mic_tool():
    if shutil.which('wpctl'):
        return 'wpctl'
    elif shutil.which('pactl'):
        return 'pactl'
    return None

def _mute_mic(mute=True):
    tool = _get_mic_tool()
    if tool == 'wpctl':
        subprocess.run(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SOURCE@', '1' if mute else '0'])
    elif tool == 'pactl':
        source = subprocess.run(
            "pactl get-default-source", 
            shell=True, capture_output=True, text=True
        ).stdout.strip()
        subprocess.run(['pactl', 'set-source-mute', source, '1' if mute else '0'])
    return tool

def block_device(device):
    if device == "cam" or device == "camera":
        result = subprocess.run(['sudo', 'modprobe', '-r', 'uvcvideo'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📷 Camera blocked")
        else:
            print(f"📷 Failed: {result.stderr.strip()}")
    elif device == "mic":
        tool = _mute_mic(True)
        print(f"🎤 Microphone blocked ({tool})")
    else:
        print("Usage: dot block <cam|mic>")

def unblock_device(device):
    if device == "cam" or device == "camera":
        result = subprocess.run(['sudo', 'modprobe', 'uvcvideo'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📷 Camera unblocked")
        else:
            print(f"📷 Failed: {result.stderr.strip()}")
    elif device == "mic":
        tool = _mute_mic(False)
        print(f"🎤 Microphone unblocked ({tool})")
    else:
        print("Usage: dot unblock <cam|mic>")

def kill_all(device=None):
    if device in ['cam', 'camera', 'webcam', 'video']:
        device = 'cam'
    elif device in ['mic', 'microphone', 'audio']:
        device = 'mic'
    
    if device == "mic" or device is None:
        devices = glob.glob('/dev/snd/pcm*')
        for dev in devices:
            subprocess.run(['fuser', '-k', dev])
    if device == "cam" or device is None:
        subprocess.run(['fuser', '-k', '/dev/video0'])
    
    if device:
        print(f"☠️ All apps using {device} killed")
    else:
        print("☠️ All apps using devices killed")

def show_history():
    db_path = "/opt/dot/data/dot.db"
    if os.path.exists(db_path):
        subprocess.run(['sqlite3', db_path, 
            "SELECT timestamp, device, process, duration FROM access_log WHERE duration > 0 ORDER BY timestamp DESC LIMIT 20;"])
    else:
        print("No history yet")

def open_settings():
    subprocess.run(['python3', '/opt/dot/show_window.py', 'settings'])

def start_web():
    def open_browser():
        time.sleep(1)
        webbrowser.open('http://localhost:8080')
    
    threading.Thread(target=open_browser).start()
    subprocess.run([sys.executable, '/opt/dot/web/app.py'])

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
        if device in ['cam', 'camera']:
            device = 'cam'
        block_device(device)
    elif cmd == "unblock":
        device = sys.argv[2] if len(sys.argv) > 2 else None
        if device in ['cam', 'camera']:
            device = 'cam'
        unblock_device(device)
    elif cmd == "kill":
        device = sys.argv[2] if len(sys.argv) > 2 else None
        kill_all(device)
    elif cmd == "history":
        show_history()
    elif cmd == "settings":
        open_settings()
    elif cmd == "install":
        subprocess.run(['bash', '/opt/dot/install.sh'])
    elif cmd == "uninstall":
        print("Run: sudo chattr -i /opt/dot/main.py /opt/dot/core/*.py && sudo rm -rf /opt/dot")
    elif cmd == "help":
        print_help()
    elif cmd == "web":
        start_web()
    else:
        print(f"Unknown command: {cmd}")
        print_help()

if __name__ == "__main__":
    main()
    
