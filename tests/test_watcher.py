import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_ROOT = os.path.join(PROJECT_ROOT, "dot")
if SOURCE_ROOT not in sys.path:
    sys.path.insert(0, SOURCE_ROOT)

from core.watcher import Watcher


class PipeWireParsingTests(unittest.TestCase):
    def test_pipewire_streams_are_joined_to_client_by_id(self):
        payload = [
            {
                "id": 10,
                "info": {
                    "props": {
                        "media.class": "Stream/Input/Audio",
                        "client.id": 20,
                    }
                },
            },
            {
                "id": 20,
                "info": {
                    "props": {
                        "application.name": "Sample App",
                        "application.process.id": "321",
                    }
                },
            },
            {"id": 30, "info": {"props": {"media.class": "Device"}}},
        ]
        command_result = SimpleNamespace(
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
            args=["pw-dump"],
        )
        process = Mock()
        process.name.return_value = "sample-app"
        watcher = Watcher.__new__(Watcher)
        watcher._is_foreground = Mock(return_value=True)

        with patch("core.watcher.subprocess.run", return_value=command_result), \
             patch("core.watcher.psutil.Process", return_value=process):
            streams = watcher._pipewire_stream_processes({"Stream/Input/Audio"})

        self.assertEqual(streams, [{
            "pid": "321",
            "name": "sample-app",
            "foreground": True,
        }])
        watcher._is_foreground.assert_called_once_with(321)

    def test_pipewire_parser_rejects_non_list_json(self):
        command_result = SimpleNamespace(
            returncode=0, stdout='{"unexpected": true}', stderr="", args=["pw-dump"]
        )
        watcher = Watcher.__new__(Watcher)
        with patch("core.watcher.subprocess.run", return_value=command_result):
            with self.assertRaises(ValueError):
                watcher._pipewire_stream_processes({"Stream/Input/Audio"})

    def test_disabling_device_monitor_clears_stale_tracking(self):
        watcher = Watcher.__new__(Watcher)
        watcher.config = {}
        watcher.active_devices = {}
        watcher.previous_mic_pids = {"321"}
        watcher.previous_cam_pids = {"654"}
        watcher.previous_scr_pids = {"987"}
        watcher.mic_start_time = {"321": object()}
        watcher.cam_start_time = {"654": object()}
        watcher.scr_start_time = {"987": object()}

        with patch("core.config.load_config", return_value={"devices": {}}):
            watcher.check_all()

        self.assertEqual(watcher.previous_mic_pids, set())
        self.assertEqual(watcher.previous_cam_pids, set())
        self.assertEqual(watcher.previous_scr_pids, set())
        self.assertEqual(watcher.mic_start_time, {})
        self.assertEqual(watcher.cam_start_time, {})
        self.assertEqual(watcher.scr_start_time, {})
        self.assertEqual(watcher.active_devices, {
            "microphone": None,
            "camera": None,
            "screenshare": None,
        })


if __name__ == "__main__":
    unittest.main()
