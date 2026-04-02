from pathlib import Path
import yaml
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent 
CONFIG_PATH = Path(
    os.getenv("CONFIG_PATH", BASE_DIR / "config" / "config.yaml")
)

class Settings:
    def __init__(self):
        self._data = self._load()

        self.default_city = self._data["weather"]["default_city"]
        self.units = self._data["weather"].get("units", "metric")
        self.forecast_days = self._data["weather"].get("forecast_days", 3)
        self.forecast_hours = self._data["weather"].get("forecast_hours", 12)

        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY")

    def _load(self):
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
        
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)

settings = Settings()