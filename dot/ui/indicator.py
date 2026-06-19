import gi # type: ignore
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
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        history_item = Gtk.MenuItem(label="📊 History")
        history_item.connect("activate", self.show_history)
        self.menu.append(history_item)
        
        settings_item = Gtk.MenuItem(label="⚙️ Settings")
        settings_item.connect("activate", self.show_settings)
        self.menu.append(settings_item)

        self.menu.append(Gtk.SeparatorMenuItem())
        
        quit_item = Gtk.MenuItem(label="✕ Quit")
        quit_item.connect("activate", self.quit)
        self.menu.append(quit_item)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        
        GLib.timeout_add(1000, self.update)
    
    def create_icon(self, status):
        import cairo # pyright: ignore[reportMissingImports]
        import os
        
        size = 16
        color_map = {
            'idle': self.config['colors']['idle'],
            'active': self.config['colors']['active'],
            'multiple': self.config['colors']['multiple']
        }
        color_hex = color_map.get(status, self.config['colors']['idle'])
        
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        cr = cairo.Context(surface)
        
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        
        cr.set_source_rgb(r/255, g/255, b/255)
        cr.arc(size/2, size/2, size/2 - 2, 0, 2 * 3.14159)
        cr.fill()
        
        cr.set_source_rgba(1, 1, 1, 0.4)
        cr.set_line_width(1)
        cr.arc(size/2, size/2, size/2 - 2, 0, 2 * 3.14159)
        cr.stroke()
        
        filename = f"/tmp/dot_{status}.png"
        surface.write_to_png(filename)
        
        return filename
    
    def update(self):
        self.config = load_config()

        status, processes = self.watcher.get_status()
        
        self.indicator.set_icon_full(self.create_icon(status), "Dot")
        
        if processes:
            for device, procs in self.watcher.active_devices.items():
                if procs:
                    names = [p['name'] for p in procs]
                    text = f"{device.capitalize()}: {', '.join(names)}"
                    if device == 'microphone':
                        self.mic_item.set_label(text)
                    elif device == 'camera':
                        self.cam_item.set_label(text)
        else:
            self.mic_item.set_label("Microphone: Inactive")
            self.cam_item.set_label("Camera: Inactive")
        
        return True

    def show_history(self, widget):
        import subprocess
        import os
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "show_window.py")
        subprocess.Popen(["python3", script, "history"])    

    def show_settings(self, widget):
        import subprocess
        import os
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "show_window.py")
        subprocess.Popen(["python3", script, "settings"])

    def quit(self, widget):
        Gtk.main_quit()
