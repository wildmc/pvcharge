import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class Config:
    raw: Dict[str, Any]

    @staticmethod
    def load(path: str = "config.yaml") -> "Config":
        Config.load_env_file()

        config_path = Config.resolve_config_path(path)
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return Config(raw=data)

    @staticmethod
    def load_env_file(path: str = ".env") -> None:
        env_path = Config.resolve_env_path(path)
        if env_path is None:
            return

        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if key and key not in os.environ:
                    os.environ[key] = value

    @staticmethod
    def resolve_config_path(path: str) -> Path:
        candidates = [
            Path(path),
            Path(__file__).resolve().parent / path,
            Path(__file__).resolve().parent.parent / path,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return Path(path)

    @staticmethod
    def resolve_env_path(path: str) -> Path | None:
        candidates = [
            Path(path),
            Path(__file__).resolve().parent / path,
            Path(__file__).resolve().parent.parent / path,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

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

    def get_secret(self, env_name, *keys, default=None):
        value = os.getenv(env_name)
        if value:
            return value
        return self.get(*keys, default=default)

    def require_secret(self, env_name, *keys):
        value = self.get_secret(env_name, *keys, default=None)
        if value is None:
            raise ValueError(
                f"Missing secret: set {env_name} or config key {'.'.join(keys)}"
            )
        return value
