import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import sqlite3
import os
import yaml
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class HistoryWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Dot - History")
        self.set_default_size(650, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("show", self.on_show)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        self.add(vbox)
        
        title = Gtk.Label(label="📊 Device Access History")
        vbox.pack_start(title, False, False, 0)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        vbox.pack_start(self.scrolled, True, True, 0)
        
        self.listbox = Gtk.ListBox()
        self.scrolled.add(self.listbox)
        
        refresh_btn = Gtk.Button(label="🔄 Refresh")
        refresh_btn.connect("clicked", lambda x: self.load_history())
        vbox.pack_start(refresh_btn, False, False, 0)
        
        self.set_modal(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
    
    def on_show(self, widget):
        self.load_history()
    
    def load_history(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'dot.db')
        
        if not os.path.exists(db_path):
            self.add_row("No database yet.")
            self.listbox.show_all()
            return
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT timestamp, device, process, duration FROM access_log ORDER BY timestamp DESC LIMIT 50")
            records = cursor.fetchall()
            
            if not records:
                self.add_row("No records found.")
            else:
                self.add_row("  TIME                | DEVICE      | PROCESS             | DURATION")
                self.add_row("  " + "─" * 70)
                for timestamp, device, process, duration in records:
                    self.add_row(f"  {timestamp:20} | {device:10} | {process:20} | {duration}s")
            
            conn.close()
        except Exception as e:
            self.add_row(f"Error: {e}")
        
        self.listbox.show_all()
    
    def add_row(self, text):
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=text)
        label.set_margin_top(3)
        label.set_margin_bottom(3)
        label.set_halign(Gtk.Align.START)
        row.add(label)
        self.listbox.add(row)

class SettingsWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Dot - Settings")
        self.set_default_size(420, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_modal(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.connect("show", self.on_show)
        
        self.config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.yaml'))
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(15)
        vbox.set_margin_bottom(15)
        vbox.set_margin_start(15)
        vbox.set_margin_end(15)
        self.add(vbox)
        
        title = Gtk.Label(label="⚙️ Dot Settings")
        vbox.pack_start(title, False, False, 0)
        
        devices_frame = Gtk.Frame(label="Devices to Monitor")
        devices_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        devices_box.set_margin_top(10)
        devices_box.set_margin_bottom(10)
        devices_box.set_margin_start(10)
        devices_box.set_margin_end(10)
        devices_frame.add(devices_box)
        
        self.mic_check = Gtk.CheckButton(label="🎤 Microphone")
        devices_box.pack_start(self.mic_check, False, False, 0)
        
        self.cam_check = Gtk.CheckButton(label="📷 Camera")
        devices_box.pack_start(self.cam_check, False, False, 0)
        
        self.loc_check = Gtk.CheckButton(label="📍 Location (coming soon)")
        self.loc_check.set_sensitive(False)
        devices_box.pack_start(self.loc_check, False, False, 0)
        
        self.scr_check = Gtk.CheckButton(label="🖥️ Screenshare (coming soon)")
        self.scr_check.set_sensitive(False)
        devices_box.pack_start(self.scr_check, False, False, 0)
        
        vbox.pack_start(devices_frame, False, False, 0)
        
        colors_frame = Gtk.Frame(label="Indicator Colors (hex)")
        colors_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        colors_box.set_margin_top(10)
        colors_box.set_margin_bottom(10)
        colors_box.set_margin_start(10)
        colors_box.set_margin_end(10)
        colors_frame.add(colors_box)
        
        self.color_entries = {}
        color_labels = [
            ('active', '🟢 Active (single app)'),
            ('multiple', '🟠 Multiple (several apps)'),
            ('idle', '⚪ Idle (no activity)')
        ]
        
        for key, label_text in color_labels:
            hbox = Gtk.Box(spacing=10)
            label = Gtk.Label(label=label_text)
            hbox.pack_start(label, False, False, 0)
            entry = Gtk.Entry()
            entry.set_max_length(7)
            entry.set_width_chars(8)
            hbox.pack_end(entry, False, False, 0)
            self.color_entries[key] = entry
            colors_box.pack_start(hbox, False, False, 0)
        
        vbox.pack_start(colors_frame, False, False, 0)
        
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.END)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda x: self.destroy())
        btn_box.pack_start(cancel_btn, False, False, 0)
        
        save_btn = Gtk.Button(label="💾 Save")
        save_btn.connect("clicked", self.on_save)
        btn_box.pack_start(save_btn, False, False, 0)
        
        vbox.pack_end(btn_box, False, False, 0)
    
    def on_show(self, widget):
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        self.mic_check.set_active(config['devices']['microphone'])
        self.cam_check.set_active(config['devices']['camera'])
        for key, entry in self.color_entries.items():
            entry.set_text(config['colors'][key])
    
    def on_save(self, button):
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        config['devices']['microphone'] = self.mic_check.get_active()
        config['devices']['camera'] = self.cam_check.get_active()
        for key, entry in self.color_entries.items():
            config['colors'][key] = entry.get_text()
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        self.destroy()
