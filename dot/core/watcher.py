import json
import psutil
import re
import subprocess

from datetime import datetime

from core.logger import Logger
from core.notifier import Notifier


class Watcher:
    def __init__(self, config):
        self.config = config
        self.active_devices = {}

        self.logger = Logger()
        self.notifier = Notifier()

        self.previous_mic_pids = set()
        self.previous_cam_pids = set()

        self.mic_start_time = {}
        self.cam_start_time = {}

    def check_all(self, notify=True):
        """
        Refresh the state of all enabled devices.

        notify=False is used by CLI status so simply checking status
        does not generate notifications or alter history.
        """
        from core.config import load_config

        self.config = load_config()

        if self.config["devices"].get("microphone", False):
            self.check_microphone(notify=notify)

        else:
            self.active_devices["microphone"] = None

        if self.config["devices"].get("camera", False):
            self.check_camera(notify=notify)

        else:
            self.active_devices["camera"] = None

        return True

    def check_microphone(self, notify=True):
        """
        Detect applications using microphone through PipeWire.
        """
        try:
            result = subprocess.run(
                ["pw-dump"],
                capture_output=True,
                text=True,
                timeout=3
            )

            if result.returncode != 0:
                self.active_devices["microphone"] = None
                return

            data = json.loads(result.stdout)

            processes = []

            for obj in data:
                info = obj.get("info", {})
                props = info.get("props", {})

                # Only actual audio input streams count as microphone usage.
                media_class = props.get("media.class", "")

                if media_class != "Stream/Input/Audio":
                    continue

                client_id = props.get("client.id")

                if not client_id:
                    continue

                for client_obj in data:
                    if str(client_obj.get("id", "")) != str(client_id):
                        continue

                    client_props = client_obj.get("info", {}).get("props", {})

                    app_name = client_props.get(
                        "application.name",
                        "unknown"
                    )

                    app_pid = client_props.get(
                        "application.process.id"
                    )

                    if not app_pid:
                        break

                    try:
                        pid = int(app_pid)
                        proc = psutil.Process(pid)

                        processes.append({
                            "pid": str(pid),
                            "name": proc.name() or app_name,
                            "foreground": self._is_foreground(pid)
                        })

                    except (ValueError, psutil.Error):
                        pass

                    break

            unique_processes = self._unique_processes(processes)

            self.active_devices["microphone"] = (
                unique_processes if unique_processes else None
            )

            current_pids = {
                p["pid"] for p in unique_processes
            }

            if notify:
                self._process_device_changes(
                    device="microphone",
                    current_pids=current_pids,
                    previous_pids=self.previous_mic_pids,
                    start_times=self.mic_start_time
                )

            self.previous_mic_pids = current_pids

        except (
            subprocess.SubprocessError,
            json.JSONDecodeError,
            OSError,
            ValueError
        ) as e:
            print(f"[MIC] Error: {e}")
            self.active_devices["microphone"] = None

    def check_camera(self, notify=True):
        """
        Detect applications currently using video devices.
        """
        try:
            result = subprocess.run(
                ["fuser", "/dev/video0"],
                capture_output=True,
                text=True,
                timeout=3
            )

            output = f"{result.stdout}\n{result.stderr}"

            # fuser can print PIDs in different formats depending on version.
            numbers = re.findall(r"\b(\d+)\b", output)

            processes = []

            for pid_str in numbers:
                try:
                    pid = int(pid_str)

                    if pid <= 1:
                        continue

                    proc = psutil.Process(pid)
                    proc_name = proc.name()

                    # PipeWire infrastructure itself is not the application
                    # using the camera.
                    if proc_name.lower() in {
                        "pipewire",
                        "wireplumber",
                        "pulseaudio"
                    }:
                        continue

                    processes.append({
                        "pid": str(pid),
                        "name": proc_name,
                        "foreground": self._is_foreground(pid)
                    })

                except (ValueError, psutil.Error):
                    pass

            unique_processes = self._unique_processes(processes)

            self.active_devices["camera"] = (
                unique_processes if unique_processes else None
            )

            current_pids = {
                p["pid"] for p in unique_processes
            }

            if notify:
                self._process_device_changes(
                    device="camera",
                    current_pids=current_pids,
                    previous_pids=self.previous_cam_pids,
                    start_times=self.cam_start_time
                )

            self.previous_cam_pids = current_pids

        except (subprocess.SubprocessError, OSError) as e:
            print(f"[CAM] Error: {e}")
            self.active_devices["camera"] = None

    def _process_device_changes(
        self,
        device,
        current_pids,
        previous_pids,
        start_times
    ):
        """
        Handle start/end events, notifications and history logging.
        """

        # Newly active applications.
        started_pids = current_pids - previous_pids

        for pid in started_pids:
            start_times[pid] = datetime.now()

        # Applications that stopped using the device.
        stopped_pids = previous_pids - current_pids

        for pid in stopped_pids:
            start = start_times.pop(pid, None)

            if start is None:
                continue

            duration = int(
                (datetime.now() - start).total_seconds()
            )

            if duration > 0:
                self.logger.log_access(
                    device,
                    "ended",
                    pid,
                    duration
                )

        # Notifications for newly started applications.
        processes = self.active_devices.get(device) or []

        process_by_pid = {
            p["pid"]: p for p in processes
        }

        for pid in started_pids:
            process = process_by_pid.get(pid)

            if process:
                self.notifier.notify(
                    device,
                    process["name"],
                    "started"
                )

                self.logger.log_access(
                    device,
                    process["name"],
                    pid
                )

        # One release notification when a process stops.
        for pid in stopped_pids:
            self.notifier.notify(
                device,
                "unknown",
                "stopped"
            )

    @staticmethod
    def _unique_processes(processes):
        seen = set()
        result = []

        for process in processes:
            pid = process["pid"]

            if pid in seen:
                continue

            seen.add(pid)
            result.append(process)

        return result

    def _is_foreground(self, pid):
        try:
            result = subprocess.run(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--dest",
                    "org.gnome.Shell",
                    "--object-path",
                    "/org/gnome/Shell",
                    "--method",
                    "org.gnome.Shell.Eval",
                    'global.display.focus_window?.get_wm_class() || ""'
                ],
                capture_output=True,
                text=True,
                timeout=2
            )

            if not result.stdout or "'" not in result.stdout:
                return False

            parts = result.stdout.split("'")

            if len(parts) < 2:
                return False

            active_class = parts[1].lower()

            if not active_class:
                return False

            try:
                proc_name = psutil.Process(int(pid)).name().lower()
            except (ValueError, psutil.Error):
                return False

            return (
                proc_name in active_class
                or active_class in proc_name
            )

        except (
            subprocess.SubprocessError,
            OSError,
            ValueError
        ):
            return False

    def get_status(self):
        """
        Return overall Dot status.
        """
        all_processes = []

        for processes in self.active_devices.values():
            if processes:
                all_processes.extend(processes)

        if not all_processes:
            return "idle", None

        unique_pids = {
            p["pid"] for p in all_processes
        }

        if len(unique_pids) > 1:
            return "multiple", all_processes

        return "active", all_processes
