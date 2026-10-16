"""Configuration loading and persistence for Dot."""

import json
import os
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "devices": {
        "camera": True,
        "microphone": True,
        "location": True,
        "screenshare": True,
    },
    "settings": {
        "auto_delete_logs": 30,
        "check_interval": 0.8,
        "startup_check_interval": 1.0,
        "auto_start": False,
    },
    "notifications": {
        "camera": False,
        "microphone": False,
        "screenshare": False,
    },
}


def _copy_defaults():
    # JSON round-tripping creates independent nested dictionaries without
    # requiring Python 3.9's dict union or newer standard-library helpers.
    return json.loads(json.dumps(DEFAULT_CONFIG))


def _is_compatible_value(value, default):
    """Check a known setting's type without accepting bool as an integer."""
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, (int, float)):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, type(default))


def _merge_defaults(config):
    """Fill missing defaults and replace malformed known values safely.

    Unknown keys are preserved to avoid discarding settings added by newer
    versions or third-party integrations.
    """
    if not isinstance(config, dict):
        config = {}

    merged = _copy_defaults()
    for section, values in config.items():
        if section not in DEFAULT_CONFIG:
            merged[section] = values
            continue

        defaults = DEFAULT_CONFIG[section]
        if not isinstance(defaults, dict):
            if _is_compatible_value(values, defaults):
                merged[section] = values
            continue

        if not isinstance(values, dict):
            continue

        target = merged[section]
        for key, value in values.items():
            if key not in defaults:
                target[key] = value
            elif _is_compatible_value(value, defaults[key]):
                target[key] = value
        merged[section] = target

    return merged


def load_config():
    """Load config, adding missing defaults without rewriting unchanged files."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            original = json.load(handle)
    except FileNotFoundError:
        config = _copy_defaults()
        save_config(config)
        return config
    except (json.JSONDecodeError, OSError):
        config = _copy_defaults()
        save_config(config)
        return config

    config = _merge_defaults(original)
    if config != original:
        save_config(config)
    return config


def save_config(config):
    """Persist config atomically so readers never observe a partial JSON file."""
    config = _merge_defaults(config)
    directory = os.path.dirname(CONFIG_PATH) or "."
    os.makedirs(directory, exist_ok=True)

    existing_mode = None
    try:
        existing_mode = os.stat(CONFIG_PATH).st_mode & 0o777
    except OSError:
        pass

    file_descriptor, temporary_path = tempfile.mkstemp(
        prefix=".config-", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=4, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary_path, existing_mode if existing_mode is not None else 0o644)
        os.replace(temporary_path, CONFIG_PATH)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise
