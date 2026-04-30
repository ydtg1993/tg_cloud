import json
from pathlib import Path

DEFAULT_CONFIG = {
    "current_bot": "",
    "bots": {},
    "pyrogram": {
        "api_id": None,
        "api_hash": "",
        "session_string": ""
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

    def get_current_bot(self):
        cur = self.config.get("current_bot")
        if cur and cur in self.config["bots"]:
            return self.config["bots"][cur]
        return None

    def set_current_bot(self, key):
        self.config["current_bot"] = key
        self.save()

    def add_bot(self, key, info):
        self.config["bots"][key] = info
        self.save()

    def remove_bot(self, key):
        if key in self.config["bots"]:
            del self.config["bots"][key]
            if self.config["current_bot"] == key:
                self.config["current_bot"] = ""
            self.save()