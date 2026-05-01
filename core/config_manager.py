import json
from pathlib import Path

DEFAULT_CONFIG = {
    "pyrogram": {
        "api_id": None,
        "api_hash": "",
        "session_string": "",
        "chat_id": ""
    },
    "download_path": str(Path.home() / "Downloads"),
    "theme": "dark",
    "clipboard_enabled": True
}


class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self.load()

    def load(self):
        if not Path(self.config_path).exists():
            return DEFAULT_CONFIG.copy()
        with open(self.config_path, "r") as f:
            return json.load(f)

    def save(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
