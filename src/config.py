import yaml
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Config:
    raw: Dict[str, Any]

    @staticmethod
    def load(path: str = "config.yaml") -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return Config(raw=data)

    def get(self, *keys, default=None):
        """
        Zugriff: config.get("control", "poll_interval")
        """
        value = self.raw
        for k in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(k, None)
            if value is None:
                return default
        return value

    def require(self, *keys):
        value = self.get(*keys, default=None)
        if value is None:
            raise ValueError(f"Missing config key: {'.'.join(keys)}")
        return value
