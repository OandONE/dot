import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib
from core.config import load_config
from core.watcher import Watcher
from core.utils import update_desktop_entry
from ui.indicator import DotIndicator
import os
import sys
import subprocess

def check_single_instance():
    pid = str(os.getpid())
    pidfile = "/tmp/dot.pid"
    
    if os.path.exists(pidfile):
        with open(pidfile) as f:
            old_pid = f.read().strip()
        
        result = subprocess.run(['ps', '-p', old_pid], capture_output=True)
        if result.returncode == 0:
            print(f"Dot is already running (PID: {old_pid})")
            sys.exit(0)
    
    with open(pidfile, 'w') as f:
        f.write(pid)


def main():
    check_single_instance()
    update_desktop_entry()

    config = load_config()
    watcher = Watcher(config)
    
    GLib.timeout_add(config['settings']['check_interval'] * 1000, watcher.check_all)
    
    indicator = DotIndicator(config, watcher)
    Gtk.main()

if __name__ == "__main__":
    main()




