import json
import re
import subprocess
from datetime import datetime

import psutil

from core.logger import Logger
from core.notifier import Notifier
from desktop import get_desktop_backend


class Watcher:
    def __init__(self, config, desktop_backend=None):
        self.config = config
        self.desktop_backend = (
            desktop_backend if desktop_backend is not None else get_desktop_backend()
        )
        self.active_devices = {}
        self.logger = Logger()
        self.notifier = Notifier()
        self.previous_mic_pids = set()
        self.previous_cam_pids = set()
        self.previous_scr_pids = set()
        self.mic_start_time = {}
        self.cam_start_time = {}
        self.scr_start_time = {}

    def check_all(self, notify=True):
        from core.config import load_config
        self.config = load_config()

        devices = self.config.get("devices", {})

        if devices.get("microphone", False):
            self.check_microphone(notify=notify)
        else:
            self._reset_device_tracking(
                "microphone", self.previous_mic_pids, self.mic_start_time
            )

        if devices.get("camera", False):
            self.check_camera(notify=notify)
        else:
            self._reset_device_tracking(
                "camera", self.previous_cam_pids, self.cam_start_time
            )

        if devices.get("screenshare", False):
            self.check_screenshare(notify=notify)
        else:
            self._reset_device_tracking(
                "screenshare", self.previous_scr_pids, self.scr_start_time
            )

        return True

    def _reset_device_tracking(self, device, previous_pids, start_times):
        """Forget an observation interval when its monitor is disabled.

        Disabling monitoring is not proof that an application stopped using a
        device, so don't emit a fabricated "stopped" event. Clear stale state
        so re-enabling the monitor starts a fresh observation interval.
        """
        previous_pids.clear()
        start_times.clear()
        self.active_devices[device] = None

    # Microphone
    def check_microphone(self, notify=True):
        try:
            processes = self._pipewire_stream_processes({"Stream/Input/Audio"})
            unique_processes = self._unique_processes(processes)
            self.active_devices["microphone"] = unique_processes if unique_processes else None
            current_pids = {p["pid"] for p in unique_processes}
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
            ValueError,
            TypeError,
        ) as e:
            print(f"[MIC] Error: {e}")
            self.active_devices["microphone"] = None

    # Camera
    def check_camera(self, notify=True):
        try:
            result = subprocess.run(
                ["fuser", "/dev/video0"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            output = f"{result.stdout}\n{result.stderr}"
            numbers = re.findall(r"\b(\d+)\b", output)
            processes = []
            for pid_str in numbers:
                try:
                    pid = int(pid_str)
                    if pid <= 1:
                        continue
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                    if proc_name.lower() in {"pipewire", "wireplumber", "pulseaudio"}:
                        continue
                    processes.append({
                        "pid": str(pid),
                        "name": proc_name,
                        "foreground": self._is_foreground(pid)
                    })
                except (ValueError, psutil.Error):
                    pass
            unique_processes = self._unique_processes(processes)
            self.active_devices["camera"] = unique_processes if unique_processes else None
            current_pids = {p["pid"] for p in unique_processes}
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

    # Screenshare
    def check_screenshare(self, notify=True):
        """Detect applications sharing video streams through PipeWire."""
        try:
            processes = self._pipewire_stream_processes({
                "Stream/Output/Video",
                "Stream/Input/Video",
            })
            unique_processes = self._unique_processes(processes)
            self.active_devices["screenshare"] = unique_processes if unique_processes else None
            current_pids = {p["pid"] for p in unique_processes}
            if notify:
                self._process_device_changes(
                    device="screenshare",
                    current_pids=current_pids,
                    previous_pids=self.previous_scr_pids,
                    start_times=self.scr_start_time
                )
            self.previous_scr_pids = current_pids
        except (
            subprocess.SubprocessError,
            json.JSONDecodeError,
            OSError,
            ValueError,
            TypeError,
        ) as e:
            print(f"[SCREENSHARE] Error: {e}")
            self.active_devices["screenshare"] = None

    def _pipewire_stream_processes(self, media_classes):
        """Map matching PipeWire streams to their client processes.

        Building a client index avoids repeatedly scanning the complete pw-dump
        document for each stream. Invalid or stale entries are skipped safely.
        """
        result = subprocess.run(
            ["pw-dump"], capture_output=True, text=True, timeout=3, check=False
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, result.args, output=result.stdout, stderr=result.stderr
            )

        data = json.loads(result.stdout)
        if not isinstance(data, list):
            raise ValueError("pw-dump returned an unexpected JSON structure")

        clients_by_id = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            info = item.get("info")
            if item_id is not None and isinstance(info, dict):
                clients_by_id[str(item_id)] = item

        processes = []
        for stream in data:
            if not isinstance(stream, dict):
                continue
            info = stream.get("info")
            props = info.get("props", {}) if isinstance(info, dict) else {}
            if not isinstance(props, dict) or props.get("media.class") not in media_classes:
                continue

            client_id = props.get("client.id")
            if client_id is None:
                continue
            client = clients_by_id.get(str(client_id))
            if client is None:
                continue

            client_info = client.get("info", {})
            client_props = client_info.get("props", {}) if isinstance(client_info, dict) else {}
            if not isinstance(client_props, dict):
                continue

            app_name = client_props.get("application.name", "unknown")
            app_pid = client_props.get("application.process.id")
            if app_pid is None:
                continue

            try:
                pid = int(app_pid)
                proc = psutil.Process(pid)
                process_name = proc.name() or str(app_name)
                processes.append({
                    "pid": str(pid),
                    "name": process_name,
                    "foreground": self._is_foreground(pid),
                })
            except (TypeError, ValueError, psutil.Error):
                # Clients can exit between pw-dump and process inspection.
                continue

        return processes

    def _process_device_changes(self, device, current_pids, previous_pids, start_times):
        started_pids = current_pids - previous_pids
        for pid in started_pids:
            start_times[pid] = datetime.now()
        stopped_pids = previous_pids - current_pids
        for pid in stopped_pids:
            start = start_times.pop(pid, None)
            if start is None:
                continue
            duration = int((datetime.now() - start).total_seconds())
            if duration > 0:
                self.logger.log_access(device, "ended", pid, duration)
        processes = self.active_devices.get(device) or []
        process_by_pid = {p["pid"]: p for p in processes}
        for pid in started_pids:
            process = process_by_pid.get(pid)
            if process:
                self.notifier.notify(device, process["name"], "started")
                self.logger.log_access(device, process["name"], pid)
        for pid in stopped_pids:
            self.notifier.notify(device, "unknown", "stopped")

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
        """Delegate foreground-window detection to the active desktop backend."""
        try:
            return bool(self.desktop_backend.is_foreground_process(int(pid)))
        except Exception:
            # Desktop integrations are optional; failure to query focus must not
            # interrupt microphone/camera/screen activity detection.
            return False

    def get_status(self):
        all_processes = []
        for processes in self.active_devices.values():
            if processes:
                all_processes.extend(processes)
        if not all_processes:
            return "idle", None
        unique_pids = {p["pid"] for p in all_processes}
        if len(unique_pids) > 1:
            return "multiple", all_processes
        return "active", all_processes
