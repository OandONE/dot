"""GNOME-specific desktop integration."""

from typing import Optional, Tuple

import shutil
import subprocess
import time

import psutil

from desktop.base import DesktopBackend


class GnomeBackend(DesktopBackend):
    """Desktop integration backed by GNOME Shell's session D-Bus API."""

    def __init__(self) -> None:
        super().__init__("gnome")
        self._active_class: Optional[str] = None
        self._active_class_checked_at = 0.0
        # Several processes may be checked during a single polling pass. Avoid
        # spawning one gdbus process for every process in that pass.
        self._active_class_cache_seconds = 0.4

    def _get_active_window_class(self) -> Optional[str]:
        now = time.monotonic()
        if now - self._active_class_checked_at < self._active_class_cache_seconds:
            return self._active_class

        self._active_class_checked_at = now
        self._active_class = None
        try:
            result = subprocess.run(
                [
                    "gdbus", "call", "--session",
                    "--dest", "org.gnome.Shell",
                    "--object-path", "/org/gnome/Shell",
                    "--method", "org.gnome.Shell.Eval",
                    'global.display.focus_window?.get_wm_class() || ""',
                ],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        if result.returncode != 0 or not result.stdout:
            return None

        # gdbus normally prints a tuple such as: (true, 'Firefox'). Preserve
        # compatibility with the format this project previously consumed.
        parts = result.stdout.split("'")
        if len(parts) >= 2 and parts[1].strip():
            self._active_class = parts[1].strip().lower()
        return self._active_class

    def is_foreground_process(self, pid: int) -> bool:
        active_class = self._get_active_window_class()
        if not active_class:
            return False

        try:
            process_name = psutil.Process(int(pid)).name().lower()
        except (TypeError, ValueError, psutil.Error):
            return False

        if not process_name:
            return False
        return process_name in active_class or active_class in process_name

    def register_kill_switch_shortcut(
        self, command: str, binding: str = "<Ctrl><Shift>K"
    ) -> Tuple[bool, str]:
        """Register Dot's kill shortcut through GNOME's GSettings schema."""
        if not shutil.which("gsettings"):
            return False, "gsettings is unavailable; configure the shortcut manually."

        parent_schema = "org.gnome.settings-daemon.plugins.media-keys"
        shortcut_path = parent_schema + ".custom-keybinding"
        key_path = (
            "/org/gnome/settings-daemon/plugins/media-keys/"
            "custom-keybindings/custom-dot/"
        )

        try:
            current = subprocess.run(
                ["gsettings", "get", parent_schema, "custom-keybindings"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if current.returncode != 0:
                return False, "GNOME custom shortcut settings are unavailable."

            current_value = current.stdout.strip()
            if key_path not in current_value:
                if current_value in ("[]", "@as []"):
                    updated_value = "['" + key_path + "']"
                elif current_value.startswith("[") and current_value.endswith("]"):
                    updated_value = current_value[:-1].rstrip() + ", '" + key_path + "']"
                else:
                    return False, "Could not safely update GNOME's shortcut list."

                updated = subprocess.run(
                    ["gsettings", "set", parent_schema, "custom-keybindings", updated_value],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                if updated.returncode != 0:
                    return False, "Could not add Dot to GNOME's custom shortcut list."

            values = (
                ("name", "Dot Kill Switch"),
                ("command", command),
                ("binding", binding),
            )
            for key, value in values:
                result = subprocess.run(
                    ["gsettings", "set", shortcut_path + ":" + key_path, key, value],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                if result.returncode != 0:
                    details = result.stderr.strip()
                    suffix = " " + details if details else ""
                    return False, "Could not configure GNOME's Dot shortcut." + suffix

        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"Could not configure GNOME's Dot shortcut: {exc}"

        return True, "GNOME Kill Switch shortcut registered (Ctrl+Shift+K)."

    def stop_screenshare(self) -> Tuple[bool, str]:
        """Stop GNOME Shell's own screencast, with its legacy shortcut fallback."""
        try:
            result = subprocess.run(
                [
                    "gdbus", "call", "--session",
                    "--dest", "org.gnome.Shell.Screencast",
                    "--object-path", "/org/gnome/Shell/Screencast",
                    "--method", "org.gnome.Shell.Screencast.Stop",
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if result.returncode == 0:
                return True, "GNOME screen recording stop request sent."
        except (OSError, subprocess.SubprocessError):
            pass

        # This shortcut only controls GNOME's built-in screen recorder. It is
        # not a general way to stop portal-based sharing in conferencing apps.
        if shutil.which("xdotool"):
            try:
                result = subprocess.run(
                    ["xdotool", "key", "Ctrl+Alt+Shift+R"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                if result.returncode == 0:
                    return True, "Sent GNOME's screen-recording shortcut."
            except (OSError, subprocess.SubprocessError):
                pass

        return False, (
            "Could not stop GNOME's built-in screen recording automatically. "
            "For application-based sharing, stop sharing in that application."
        )
