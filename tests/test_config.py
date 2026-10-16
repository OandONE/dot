import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_ROOT = os.path.join(PROJECT_ROOT, "dot")
if SOURCE_ROOT not in sys.path:
    sys.path.insert(0, SOURCE_ROOT)

from core import config


class ConfigTests(unittest.TestCase):
    def test_merge_defaults_repairs_malformed_known_sections(self):
        merged = config._merge_defaults({
            "devices": None,
            "settings": {"check_interval": "fast", "auto_start": 1},
            "third_party": {"enabled": True},
        })
        self.assertIs(merged["devices"]["camera"], True)
        self.assertEqual(merged["settings"]["check_interval"], 0.8)
        self.assertIs(merged["settings"]["auto_start"], False)
        self.assertEqual(merged["third_party"], {"enabled": True})

    def test_load_config_does_not_rewrite_unchanged_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = os.path.join(temporary_directory, "config.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(config.DEFAULT_CONFIG, handle)

            with patch.object(config, "CONFIG_PATH", path):
                before = os.stat(path).st_mtime_ns
                loaded = config.load_config()
                after = os.stat(path).st_mtime_ns

            self.assertEqual(loaded, config.DEFAULT_CONFIG)
            self.assertEqual(before, after)

    def test_save_config_is_valid_json_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = os.path.join(temporary_directory, "config.json")
            with patch.object(config, "CONFIG_PATH", path):
                config.save_config({"settings": {"check_interval": 1.25}})
                loaded = config.load_config()

            self.assertEqual(loaded["settings"]["check_interval"], 1.25)
            self.assertEqual(os.listdir(temporary_directory), ["config.json"])


if __name__ == "__main__":
    unittest.main()
