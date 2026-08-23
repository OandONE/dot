import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gdk, GLib  # type: ignore

import os
import sqlite3
import subprocess
import threading
import time
import sys

from core.config import load_config, save_config
from core.utils import  is_autostart_enabled, set_autostart


def get_dot_root():
    return os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )


def get_venv_python():
    return os.path.join(
        get_dot_root(),
        ".venv",
        "bin",
        "python"
    )


def flask_installed():
    venv_python = get_venv_python()

    if not os.path.exists(venv_python):
        return False

    result = subprocess.run(
        [
            venv_python,
            "-c",
            "import flask"
        ],
        capture_output=True
    )

    return result.returncode == 0

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
        
        self.store = Gtk.ListStore(
            str,
            str,
            str,
            str
        )

        self.tree = Gtk.TreeView(
            model=self.store
        )

        columns = [
            ("Time", 0),
            ("Device", 1),
            ("Process", 2),
            ("Duration", 3)
        ]

        for title, column_id in columns:
            renderer = Gtk.CellRendererText()

            column = Gtk.TreeViewColumn(
                title,
                renderer,
                text=column_id
            )

            column.set_resizable(True)

            self.tree.append_column(column)

        self.scrolled.add(self.tree)
        
        refresh_btn = Gtk.Button(label="⟳ Refresh")
        refresh_btn.connect("clicked", lambda x: self.load_history())
        vbox.pack_start(refresh_btn, False, False, 0)
    
    def on_show(self, widget):
        self.load_history()
    
    def load_history(self):
        self.store.clear()

        db_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            "dot.db"
        )

        if not os.path.exists(db_path):
            self.store.append([
                "-",
                "-",
                "No database yet",
                "-"
            ])
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

            conn.close()

            if not records:
                self.store.append([
                    "-",
                    "-",
                    "No records found",
                    "-"
                ])
                return

            for timestamp, device, process, duration in records:
                self.store.append([
                    str(timestamp),
                    str(device),
                    str(process),
                    f"{duration}s"
                ])

        except sqlite3.Error as e:
            self.store.append([
                "-",
                "-",
                "Database error",
                str(e)
            ])

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
        self.set_default_size(420, 420)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_modal(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.connect("show", self.on_show)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(15)
        vbox.set_margin_bottom(15)
        vbox.set_margin_start(15)
        vbox.set_margin_end(15)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(vbox)
        self.add(scrolled)
        
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
        
        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_halign(Gtk.Align.END)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda x: self.destroy())
        btn_box.pack_start(cancel_btn, False, False, 0)
        
        save_btn = Gtk.Button(label="💾 Save")
        save_btn.connect("clicked", self.on_save)
        btn_box.pack_start(save_btn, False, False, 0)

        # Notifications
        notif_frame = Gtk.Frame(label="Notifications")
        notif_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        notif_box.set_margin_top(10)
        notif_box.set_margin_bottom(10)
        notif_box.set_margin_start(10)
        notif_box.set_margin_end(10)
        notif_frame.add(notif_box)
        
        self.notif_mic_check = Gtk.CheckButton(label="🔔 Microphone access")
        notif_box.pack_start(self.notif_mic_check, False, False, 0)
        
        self.notif_cam_check = Gtk.CheckButton(label="🔔 Camera access")
        notif_box.pack_start(self.notif_cam_check, False, False, 0)
        
        vbox.pack_start(notif_frame, False, False, 0)
        
        vbox.pack_end(btn_box, False, False, 0)

        # Web Panel
        web_frame = Gtk.Frame(label="Web Panel")
        web_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        web_box.set_margin_top(10)
        web_box.set_margin_bottom(10)
        web_box.set_margin_start(10)
        web_box.set_margin_end(10)
        web_frame.add(web_box)
        
        web_label = Gtk.Label(label="Monitor your devices from browser")
        web_box.pack_start(web_label, False, False, 0)
        
        web_btn = Gtk.Button.new_with_label("Open Web Panel (localhost:8080)")
        web_btn.connect("clicked", self.on_open_web)
        web_box.pack_start(web_btn, False, False, 0)
        
        vbox.pack_start(web_frame, False, False, 0)

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
        self.interval_spin.set_value(0.5)
        self.interval_spin.connect("value-changed", self.on_interval_changed)
        hbox.pack_end(self.interval_spin, False, False, 0)
        interval_box.pack_start(hbox, False, False, 0)
        
        self.interval_label = Gtk.Label(label="")
        interval_box.pack_start(self.interval_label, False, False, 0)
        self.on_interval_changed(self.interval_spin)
        
        vbox.pack_start(interval_frame, False, False, 0)

    def on_flask_install_finished(self, success, error):
        if not success:
            self.show_error(
                "Could not install Flask.",
                error
            )
            return

        self.start_web_panel(
            get_venv_python()
        )

    def start_web_panel(self, python_executable):
        web_app = os.path.join(
            get_dot_root(),
            "web",
            "app.py"
        )

        def start():
            result = subprocess.run(
                ["fuser", "8080/tcp"],
                capture_output=True
            )

            if result.returncode != 0:
                subprocess.Popen([
                    python_executable,
                    web_app
                ])

                time.sleep(1)

            subprocess.run([
                "xdg-open",
                "http://localhost:8080"
            ])

        threading.Thread(
            target=start,
            daemon=True
        ).start()

    def install_flask_async(self, venv_python, callback):
        """
        Install Flask in a background thread while keeping
        the GTK interface responsive.
        """

        progress_dialog = Gtk.Dialog(
            title="Installing Flask",
            transient_for=self,
            modal=True
        )

        progress_dialog.set_default_size(
            400,
            150
        )

        content = progress_dialog.get_content_area()

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )

        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)

        label = Gtk.Label(
            label="Installing Flask..."
        )

        label.set_halign(Gtk.Align.START)

        progress = Gtk.ProgressBar()

        info = Gtk.Label(
            label="Please wait. This may take a little while."
        )

        info.set_halign(Gtk.Align.START)

        box.pack_start(
            label,
            False,
            False,
            0
        )

        box.pack_start(
            progress,
            False,
            False,
            0
        )

        box.pack_start(
            info,
            False,
            False,
            0
        )

        content.add(box)
        progress_dialog.show_all()

        pulse_source = GLib.timeout_add(
            100,
            lambda: self._pulse_progress(progress)
        )

        def finish(success, error):
            try:
                GLib.source_remove(
                    pulse_source
                )
            except Exception:
                pass

            progress_dialog.destroy()

            callback(
                success,
                error
            )

            return False

        def install():
            try:
                result = subprocess.run(
                    [
                        venv_python,
                        "-m",
                        "pip",
                        "install",
                        "Flask"
                    ],
                    capture_output=True,
                    text=True
                )

                success = (
                    result.returncode == 0
                )

                error = (
                    result.stderr.strip()
                    if result.stderr
                    else ""
                )

            except Exception as e:
                success = False
                error = str(e)

            GLib.idle_add(
                finish,
                success,
                error
            )

        threading.Thread(
            target=install,
            daemon=True
        ).start()


    def _pulse_progress(self, progress):
        progress.pulse()
        return True

    def show_error(self, title, details):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )

        if details:
            dialog.format_secondary_text(
                details.strip()
            )

        dialog.run()
        dialog.destroy()
    
    def on_show(self, widget):
        config = load_config()

        devices = config.get("devices", {})
        settings = config.get("settings", {})
        notifications = config.get("notifications", {})

        self.mic_check.set_active(
            devices.get("microphone", True)
        )

        self.cam_check.set_active(
            devices.get("camera", True)
        )

        self.autostart_check.set_active(
            is_autostart_enabled()
        )

        self.notif_mic_check.set_active(
            notifications.get("microphone", False)
        )

        self.notif_cam_check.set_active(
            notifications.get("camera", False)
        )

        self.interval_spin.set_value(
            float(settings.get("check_interval", 0.8))
        )

    def on_open_web(self, button):
        venv_dir = os.path.join(
            get_dot_root(),
            ".venv"
        )

        venv_python = get_venv_python()

        if flask_installed():
            self.start_web_panel(venv_python)
            return

        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Flask is not installed."
        )

        dialog.format_secondary_text(
            "Flask is required for the Web Panel.\n"
            "Do you want to install it for Dot?"
        )

        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.YES:
            return

        # Create venv first if necessary.
        if not os.path.exists(venv_python):

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "venv",
                    venv_dir
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.show_error(
                    "Could not create Dot virtual environment.",
                    result.stderr
                )
                return

        # Flask installation happens in background.
        self.install_flask_async(
            venv_python,
            self.on_flask_install_finished
        )
        
    def on_interval_changed(self, spin):
        val = spin.get_value()
        if val <= 0.3:
            self.interval_label.set_text("⚡ Fast (more CPU)")
        elif val <= 1.0:
            self.interval_label.set_text("✅ Balanced")
        else:
            self.interval_label.set_text("🐢 Slow (less CPU)")

    def on_save(self, button):
        config = load_config()

        if "devices" not in config:
            config["devices"] = {}

        if "settings" not in config:
            config["settings"] = {}

        if "notifications" not in config:
            config["notifications"] = {}

        config["devices"]["microphone"] = (
            self.mic_check.get_active()
        )

        config["devices"]["camera"] = (
            self.cam_check.get_active()
        )

        config["settings"]["check_interval"] = (
            self.interval_spin.get_value()
        )

        config["settings"]["auto_start"] = (
            self.autostart_check.get_active()
        )

        config["notifications"]["microphone"] = (
            self.notif_mic_check.get_active()
        )

        config["notifications"]["camera"] = (
            self.notif_cam_check.get_active()
        )

        save_config(config)

        # Apply startup setting immediately.
        set_autostart(
            self.autostart_check.get_active()
        )

        self.destroy()
