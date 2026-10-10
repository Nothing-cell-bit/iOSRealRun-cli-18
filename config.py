import yaml
from pathlib import Path
import sys

class Config:
    def __init__(self):
        self.directory = (
            Path(sys.executable).resolve().parent
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent
        )
        self._config_path = self.directory / "config.yaml"
        with self._config_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        for i in config:
            setattr(self, i, config[i])

    def save(self):
        data = {
            "v": self.v,
            "routeConfig": self.routeConfig,
            "libimobiledeviceDir": self.libimobiledeviceDir,
            "imageDir": self.imageDir,
        }
        with self._config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


config = Config()
