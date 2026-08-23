import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "devices": {
        "camera": True,
        "microphone": True,
        "location": True,
        "screenshare": True
    },
    "settings": {
        "auto_delete_logs": 30,
        "check_interval": 0.8,
        "startup_check_interval": 1.0,
        "auto_start": False
    },
    "notifications": {
        "camera": False,
        "microphone": False,
        "screenshare": False
    }
}

def _merge_defaults(config):
    if not isinstance(config, dict):
        config = {}
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    for section, values in config.items():
        if isinstance(values, dict) and isinstance(merged.get(section), dict):
            merged[section].update(values)
        else:
            merged[section] = values
    return merged

def load_config():
    if not os.path.exists(CONFIG_PATH):
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        save_config(config)
        return config
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        config = _merge_defaults(config)
        save_config(config)
        return config
    except (json.JSONDecodeError, OSError):
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        save_config(config)
        return config

def save_config(config):
    config = _merge_defaults(config)
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        f.write("\n")
