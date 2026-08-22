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
                result = os.kill(
                    int(old_pid),
                    0
                )

                # If os.kill succeeded, the process exists.
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


def main():
    check_single_instance()

    config = load_config()

    watcher = Watcher(config)

    GLib.timeout_add(
        int(config["settings"]["check_interval"] * 1000),
        watcher.check_all
    )

    indicator = DotIndicator(
        config,
        watcher
    )

    Gtk.main()


if __name__ == "__main__":
    main()
