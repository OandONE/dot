import gi
gi.require_version('Gtk', '3.0')
import os
import sys
from core.utils import get_appindicator_module
module_name, version = get_appindicator_module()
gi.require_version(module_name, version)
if module_name == 'AyatanaAppIndicator3':
    from gi.repository import AyatanaAppIndicator3 as AppIndicator # type: ignore
else:
    from gi.repository import AppIndicator3 as AppIndicator # type: ignore

from gi.repository import Gtk, GLib # pyright: ignore[reportMissingImports, reportAttributeAccessIssue]

from core.config import load_config

import sys
import os
import subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HistoryWindow = None
SettingsWindow = None

class DotIndicator:
    def __init__(self, config, watcher):
    
        global HistoryWindow, SettingsWindow
        from ui.windows import HistoryWindow, SettingsWindow
        self.config = config
        self.watcher = watcher
        
        self.indicator = AppIndicator.Indicator.new(
            "dot-indicator",
            "",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        
        self.indicator.set_icon_full(self.create_icon("idle"), "Dot")
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        
        self.menu = Gtk.Menu()
        
        self.mic_item = Gtk.MenuItem(label="Microphone: Inactive")
        self.mic_item.set_sensitive(False)
        self.menu.append(self.mic_item)
        
        self.cam_item = Gtk.MenuItem(label="Camera: Inactive")
        self.cam_item.set_sensitive(False)
        self.menu.append(self.cam_item)

        self.scr_item = Gtk.MenuItem(label="Screenshare: Inactive")
        self.scr_item.set_sensitive(False)
        self.menu.append(self.scr_item)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        history_item = Gtk.MenuItem(label="📊 History")
        history_item.connect("activate", self.show_history)
        self.menu.append(history_item)
        
        settings_item = Gtk.MenuItem(label="⚙️ Settings")
        settings_item.connect("activate", self.show_settings)
        self.menu.append(settings_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.kill_item = Gtk.MenuItem(label="🚫 Kill All (Ctrl+Shift+K)")
        self.kill_item.connect("activate", lambda w: self.kill_all_devices())
        self.menu.append(self.kill_item)
        
        quit_item = Gtk.MenuItem(label="✕ Quit")
        quit_item.connect("activate", self.quit)
        self.menu.append(quit_item)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        GLib.timeout_add(1000, self.update)
    
    def create_icon(self, status):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assets_dir = os.path.join(base_dir, "assets")
        
        if status == 'active' and self.watcher:
            if self.watcher.active_devices.get('screenshare') and not any([
                self.watcher.active_devices.get('camera'),
                self.watcher.active_devices.get('microphone')
            ]):
                return os.path.join(assets_dir, 'dot-screen.svg')
            elif self.watcher.active_devices.get('camera'):
                return os.path.join(assets_dir, 'dot-cam.svg')
            elif self.watcher.active_devices.get('microphone'):
                return os.path.join(assets_dir, 'dot-mic.svg')
            elif self.watcher.active_devices.get('screenshare'):
                return os.path.join(assets_dir, 'dot-screen.svg')
        
        icon_map = {
            'idle': 'dot-idle.svg',
            'active': 'dot-mic.svg',
            'multiple': 'dot-multiple.svg'
        }
        
        filename = icon_map.get(status, 'dot-idle.svg')
        return os.path.join(assets_dir, filename)
    
    def kill_all_devices(self):
        subprocess.run(['fuser', '-k', '/dev/video0'])
        subprocess.run(['fuser', '-k', '/dev/snd/pcmC0D0c'])
        subprocess.run(['notify-send', '🛑 Dot Kill Switch', 'All devices blocked!', '--icon=security-high'])

    def update(self):
        self.config = load_config()

        status, processes = self.watcher.get_status()
        
        self.indicator.set_icon_full(self.create_icon(status), "Dot")
        
        # Mic
        mic_procs = self.watcher.active_devices.get("microphone", [])
        if mic_procs:
            names = [p['name'] for p in mic_procs]
            self.mic_item.set_label(f"Microphone: {', '.join(names)}")
        else:
            self.mic_item.set_label("Microphone: Inactive")
        
        # Camera
        cam_procs = self.watcher.active_devices.get("camera", [])
        if cam_procs:
            names = [p['name'] for p in cam_procs]
            self.cam_item.set_label(f"Camera: {', '.join(names)}")
        else:
            self.cam_item.set_label("Camera: Inactive")
        
        # ScreenShare
        scr_procs = self.watcher.active_devices.get("screenshare", [])
        if scr_procs:
            names = [p['name'] for p in scr_procs]
            self.scr_item.set_label(f"Screenshare: {', '.join(names)}")
        else:
            self.scr_item.set_label("Screenshare: Inactive")
        
        return True

    def show_history(self, widget):
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "show_window.py")
        subprocess.Popen(["python3", script, "history"])    

    def show_settings(self, widget):
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "show_window.py")
        subprocess.Popen(["python3", script, "settings"])

    def quit(self, widget):
        Gtk.main_quit()
