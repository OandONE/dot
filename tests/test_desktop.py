import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_ROOT = os.path.join(PROJECT_ROOT, "dot")
if SOURCE_ROOT not in sys.path:
    sys.path.insert(0, SOURCE_ROOT)

from desktop import DesktopBackend, GnomeBackend, detect_desktop_name, get_desktop_backend
from core.watcher import Watcher


class DesktopDetectionTests(unittest.TestCase):
    def test_detects_ubuntu_gnome_session(self):
        self.assertEqual(
            detect_desktop_name({"XDG_CURRENT_DESKTOP": "ubuntu:GNOME"}),
            "gnome",
        )

    def test_detects_lxqt_without_claiming_gnome(self):
        self.assertEqual(
            detect_desktop_name({"XDG_CURRENT_DESKTOP": "LXQt"}),
            "lxqt",
        )

    def test_detection_uses_fallback_session_variables(self):
        self.assertEqual(
            detect_desktop_name({"XDG_SESSION_DESKTOP": "plasma"}),
            "kde",
        )

    def test_current_desktop_takes_priority_over_stale_session_value(self):
        self.assertEqual(
            detect_desktop_name({
                "XDG_CURRENT_DESKTOP": "LXQt",
                "XDG_SESSION_DESKTOP": "ubuntu",
            }),
            "lxqt",
        )

    def test_xubuntu_is_not_misidentified_as_gnome(self):
        self.assertEqual(
            detect_desktop_name({"DESKTOP_SESSION": "xubuntu", "XDG_CURRENT_DESKTOP": "XFCE"}),
            "xfce",
        )

    def test_lxqt_factory_is_generic_until_lxqt_backend_exists(self):
        backend = get_desktop_backend(environ={"XDG_CURRENT_DESKTOP": "LXQt"})
        self.assertIsInstance(backend, DesktopBackend)
        self.assertNotIsInstance(backend, GnomeBackend)
        self.assertEqual(backend.name, "lxqt")

    def test_unknown_desktop_gets_safe_generic_backend(self):
        backend = get_desktop_backend(environ={"XDG_CURRENT_DESKTOP": "SomeNewDesktop"})
        self.assertIsInstance(backend, DesktopBackend)
        self.assertNotIsInstance(backend, GnomeBackend)
        self.assertEqual(backend.name, "unknown")
        self.assertFalse(backend.is_foreground_process(1234))
        success, message = backend.stop_screenshare()
        self.assertFalse(success)
        self.assertIn("not implemented", message)
        shortcut_success, shortcut_message = backend.register_kill_switch_shortcut("dot kill")
        self.assertFalse(shortcut_success)
        self.assertIn("Configure", shortcut_message)

    def test_gnome_registers_shortcut_via_gsettings(self):
        backend = GnomeBackend()
        with patch("desktop.gnome.shutil.which", return_value="/usr/bin/gsettings"), \
             patch("desktop.gnome.subprocess.run", return_value=SimpleNamespace(
                 returncode=0, stdout="[]", stderr=""
             )) as run:
            success, message = backend.register_kill_switch_shortcut("/usr/local/bin/dot kill")

        self.assertTrue(success)
        self.assertIn("registered", message)
        # One read of the keybinding list, then one list update and three fields.
        self.assertEqual(run.call_count, 5)

    def test_factory_chooses_gnome_backend(self):
        backend = get_desktop_backend(environ={"XDG_CURRENT_DESKTOP": "GNOME"})
        self.assertIsInstance(backend, GnomeBackend)

    def test_gnome_backend_compares_process_name_to_active_window_class(self):
        backend = GnomeBackend()
        with patch.object(backend, "_get_active_window_class", return_value="firefox"), \
             patch("desktop.gnome.psutil.Process") as process_factory:
            process_factory.return_value.name.return_value = "firefox"
            self.assertTrue(backend.is_foreground_process(321))

            process_factory.return_value.name.return_value = "camera-daemon"
            self.assertFalse(backend.is_foreground_process(654))

    def test_watcher_delegates_foreground_check(self):
        backend = Mock()
        backend.is_foreground_process.return_value = True
        watcher = Watcher.__new__(Watcher)
        watcher.desktop_backend = backend

        self.assertTrue(watcher._is_foreground(4321))
        backend.is_foreground_process.assert_called_once_with(4321)

    def test_watcher_handles_backend_errors(self):
        backend = Mock()
        backend.is_foreground_process.side_effect = RuntimeError("desktop service unavailable")
        watcher = Watcher.__new__(Watcher)
        watcher.desktop_backend = backend

        self.assertFalse(watcher._is_foreground(4321))


if __name__ == "__main__":
    unittest.main()
