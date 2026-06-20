import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import sqlite3
import os
import yaml
import cairo
import subprocess
import os as _os
from core.utils import update_desktop_entry

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
        
        title = Gtk.Label(label="☰ Device Access History")
        vbox.pack_start(title, False, False, 0)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        vbox.pack_start(self.scrolled, True, True, 0)
        
        self.listbox = Gtk.ListBox()
        self.scrolled.add(self.listbox)
        
        refresh_btn = Gtk.Button(label="⟳ Refresh")
        refresh_btn.connect("clicked", lambda x: self.load_history())
        vbox.pack_start(refresh_btn, False, False, 0)
    
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
            
            cursor.execute("""
                SELECT timestamp, device, process, duration 
                FROM access_log 
                WHERE duration > 0
                ORDER BY timestamp DESC 
                LIMIT 50
            """)
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
        self.set_default_size(420, 480)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_modal(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.connect("show", self.on_show)
        
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(15)
        vbox.set_margin_bottom(15)
        vbox.set_margin_start(15)
        vbox.set_margin_end(15)
        self.add(vbox)
        
        title = Gtk.Label(label="⚙ Dot Settings")
        vbox.pack_start(title, False, False, 0)
        
        # Devices
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
        
        autostart_frame = Gtk.Frame(label="Startup")
        autostart_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        autostart_box.set_margin_top(10)
        autostart_box.set_margin_bottom(10)
        autostart_box.set_margin_start(10)
        autostart_box.set_margin_end(10)
        autostart_frame.add(autostart_box)
        
        self.autostart_check = Gtk.CheckButton(label="Run Dot on system startup")
        autostart_box.pack_start(self.autostart_check, False, False, 0)
        
        vbox.pack_start(autostart_frame, False, False, 0)
        
        # Colors
        colors_frame = Gtk.Frame(label="Indicator Colors")
        colors_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        colors_box.set_margin_top(10)
        colors_box.set_margin_bottom(10)
        colors_box.set_margin_start(10)
        colors_box.set_margin_end(10)
        colors_frame.add(colors_box)
        
        self.color_entries = {}
        self.color_previews = {}
        color_labels = [
            ('active', 'Active (single app)'),
            ('multiple', 'Multiple apps'),
            ('idle', 'Idle (no activity)')
        ]
        
        for key, label_text in color_labels:
            hbox = Gtk.Box(spacing=10)
            
            # دایره رنگی با DrawingArea
            color_box = Gtk.DrawingArea()
            color_box.set_size_request(24, 24)
            color_box.connect("draw", self.on_color_preview_draw, key)
            
            # EventBox برای کلیک
            event_box = Gtk.EventBox()
            event_box.add(color_box)
            event_box.connect("button-press-event", self.on_color_box_click, key)
            hbox.pack_start(event_box, False, False, 0)
            self.color_previews[key] = color_box
            
            label = Gtk.Label(label=label_text)
            hbox.pack_start(label, False, False, 0)
            
            entry = Gtk.Entry()
            entry.set_max_length(7)
            entry.set_width_chars(8)
            entry.connect("changed", self.on_color_changed, key)
            hbox.pack_end(entry, False, False, 0)
            self.color_entries[key] = entry
            
            colors_box.pack_start(hbox, False, False, 0)
        
        vbox.pack_start(colors_frame, False, False, 0)
        
        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.END)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda x: self.destroy())
        btn_box.pack_start(cancel_btn, False, False, 0)
        
        save_btn = Gtk.Button(label="💾 Save")
        save_btn.connect("clicked", self.on_save)
        btn_box.pack_start(save_btn, False, False, 0)
        
        vbox.pack_end(btn_box, False, False, 0)

        # Sleep Interval
        interval_frame = Gtk.Frame(label="Check Interval")
        interval_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        interval_box.set_margin_top(10)
        interval_box.set_margin_bottom(10)
        interval_box.set_margin_start(10)
        interval_box.set_margin_end(10)
        interval_frame.add(interval_box)
        
        hbox = Gtk.Box(spacing=10)
        label = Gtk.Label(label="Interval (seconds):")
        hbox.pack_start(label, False, False, 0)
        
        self.interval_spin = Gtk.SpinButton.new_with_range(0.1, 5.0, 0.1)
        self.interval_spin.set_value(0.8)
        self.interval_spin.connect("value-changed", self.on_interval_changed)
        hbox.pack_end(self.interval_spin, False, False, 0)
        interval_box.pack_start(hbox, False, False, 0)
        
        self.interval_label = Gtk.Label(label="")
        interval_box.pack_start(self.interval_label, False, False, 0)
        self.on_interval_changed(self.interval_spin)
        
        vbox.pack_start(interval_frame, False, False, 0)
    
    def on_show(self, widget):
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        self.mic_check.set_active(config['devices']['microphone'])
        self.cam_check.set_active(config['devices']['camera'])
        for key, entry in self.color_entries.items():
            if key in config['colors']:
                entry.set_text(config['colors'][key])
            self.update_color_preview(key)
        autostart_path = os.path.expanduser("~/.config/autostart/dot.desktop")
        self.autostart_check.set_active(os.path.exists(autostart_path))
        if 'settings' in config and 'check_interval' in config['settings']:
            self.interval_spin.set_value(config['settings']['check_interval'])
    
    def on_color_preview_draw(self, widget, cr, key):
        color = self.color_entries[key].get_text()
        if len(color) == 7 and color.startswith('#'):
            r = int(color[1:3], 16) / 255
            g = int(color[3:5], 16) / 255
            b = int(color[5:7], 16) / 255
        else:
            r, g, b = 0.5, 0.5, 0.5
        
        cr.set_source_rgb(r, g, b)
        cr.arc(12, 12, 10, 0, 2 * 3.14159)
        cr.fill()
        
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(2)
        cr.arc(12, 12, 10, 0, 2 * 3.14159)
        cr.stroke()
    
    def on_color_box_click(self, widget, event, key):
        self.on_color_picker(None, key)
        return True
    
    def update_color_preview(self, key):
        if key in self.color_previews:
            self.color_previews[key].queue_draw()
    
    def on_color_changed(self, entry, key):
        self.update_color_preview(key)
    
    def on_color_picker(self, button, key):
        current_color = self.color_entries[key].get_text()
        dialog = Gtk.ColorChooserDialog(title="Pick Color")
        dialog.set_modal(True)
        
        if len(current_color) == 7 and current_color.startswith('#'):
            r = int(current_color[1:3], 16) / 255
            g = int(current_color[3:5], 16) / 255
            b = int(current_color[5:7], 16) / 255
            rgba = Gdk.RGBA(r, g, b, 1)
            dialog.set_rgba(rgba)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            color = dialog.get_rgba()
            hex_color = f"#{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}"
            self.color_entries[key].set_text(hex_color)
        dialog.destroy()
    
    def on_interval_changed(self, spin):
        val = spin.get_value()
        if val <= 0.3:
            self.interval_label.set_text("⚡ Fast (more CPU)")
        elif val <= 1.0:
            self.interval_label.set_text("✅ Balanced")
        else:
            self.interval_label.set_text("🐢 Slow (less CPU)")

    def on_save(self, button):
        update_desktop_entry()

        subprocess.run(['sudo', 'chattr', '-i', self.config_path])
        subprocess.run(['sudo', 'chown', _os.getenv('USER'), self.config_path]) # type: ignore

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        config['devices']['microphone'] = self.mic_check.get_active()
        config['devices']['camera'] = self.cam_check.get_active()
        for key, entry in self.color_entries.items():
            config['colors'][key] = entry.get_text()
        
        if 'settings' not in config:
            config['settings'] = {}
        config['settings']['check_interval'] = self.interval_spin.get_value()
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        # return ownership and lock
        subprocess.run(['sudo', 'chown', 'root:root', self.config_path])
        subprocess.run(['sudo', 'chattr', '+i', self.config_path])
        
        # Autostart
        autostart_dir = _os.path.expanduser("~/.config/autostart")
        autostart_file = _os.path.join(autostart_dir, "dot.desktop")
        home = _os.path.expanduser("~")
        
        if self.autostart_check.get_active():
            _os.makedirs(autostart_dir, exist_ok=True)
            with open(autostart_file, 'w') as f:
                f.write("[Desktop Entry]\n")
                f.write("Type=Application\n")
                f.write("Name=Dot\n")
                f.write("Comment=Privacy Indicator\n")
                f.write(f"Exec=python3 {home}/Dot/dot/main.py\n")
                f.write("StartupNotify=false\n")
                f.write("Terminal=false\n")
                f.write("X-GNOME-Autostart-enabled=true\n")
        else:
            if _os.path.exists(autostart_file):
                _os.remove(autostart_file)

        self.destroy()
