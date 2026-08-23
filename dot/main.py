import gi

from core.utils import get_appindicator_module

gi.require_version("Gtk", "3.0")

module_name, version = get_appindicator_module()

gi.require_version(
    module_name,
    version
)

from gi.repository import Gtk, GLib

from core.config import load_config
from core.watcher import Watcher
from ui.indicator import DotIndicator

import atexit
import os
import sys


PID_FILE = "/tmp/dot.pid"


def remove_pid_file():
    try:
        if not os.path.exists(PID_FILE):
            return

        with open(PID_FILE, "r") as f:
            pid = f.read().strip()

        if pid == str(os.getpid()):
            os.remove(PID_FILE)

    except OSError:
        pass


def check_single_instance():
    current_pid = str(os.getpid())

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = f.read().strip()

            if old_pid.isdigit():
                os.kill(int(old_pid), 0)

                print(
                    f"Dot is already running "
                    f"(PID: {old_pid})"
                )

                sys.exit(0)

        except ProcessLookupError:
            pass

        except PermissionError:
            print(
                f"Dot may already be running "
                f"(PID: {old_pid})"
            )
            sys.exit(0)

        except ValueError:
            pass

        except OSError:
            pass

    with open(PID_FILE, "w") as f:
        f.write(current_pid)

    atexit.register(remove_pid_file)


def run_watcher(watcher):
    try:
        watcher.check_all()
    except Exception as e:
        print(f"[WATCHER] Error: {e}")

    return True


def main():
    check_single_instance()

    config = load_config()

    watcher = Watcher(config)

    check_interval = float(
        config.get("settings", {}).get(
            "check_interval",
            0.5
        )
    )

    check_interval = max(
        0.1,
        min(check_interval, 5.0)
    )

    GLib.timeout_add(
        int(check_interval * 1000),
        run_watcher,
        watcher
    )

    indicator = DotIndicator(
        config,
        watcher
    )

    Gtk.main()


if __name__ == "__main__":
    main()
