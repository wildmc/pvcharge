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

        config = Config(raw=data)
        config.apply_env_overrides()
        return config

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
        project_root = Path(__file__).resolve().parent.parent
        candidates = [
            Path(path),
            project_root / path,
            Path(__file__).resolve().parent / path,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return Path(path)

    @staticmethod
    def resolve_env_path(path: str) -> Path | None:
        project_root = Path(__file__).resolve().parent.parent
        candidates = [
            Path(path),
            project_root / path,
            Path(__file__).resolve().parent / path,
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

    def set(self, *keys, value):
        target = self.raw
        for key in keys[:-1]:
            target = target.setdefault(key, {})
        target[keys[-1]] = value

    def apply_env_overrides(self):
        overrides = {
            "NEOOM_BEAAM_HOST": ("inverter", "neoom_beaam", "host"),
            "SOLAX_MODBUS_HOST": ("inverter", "solax_modbus", "host"),
            "EASEE_LOCAL_HOST": ("wallbox", "local", "host"),
            "NEOOM_BEAAM_API_TOKEN": ("inverter", "neoom_beaam", "token"),
            "EASEE_USER_NAME": ("wallbox", "cloud", "user_name"),
            "EASEE_CHARGER_ID": ("wallbox", "cloud", "charger_id"),
        }

        for env_name, keys in overrides.items():
            value = os.getenv(env_name)
            if value:
                self.set(*keys, value=value)

    def get_env(self, env_name, *keys, default=None):
        value = os.getenv(env_name)
        if value:
            return value
        return self.get(*keys, default=default)

    def require_env(self, env_name, *keys):
        value = self.get_env(env_name, *keys, default=None)
        if value:
            return value
        raise ValueError(
            f"Missing value: set {env_name} or config key {'.'.join(keys)}"
        )

    def get_secret(self, env_name, *keys, default=None):
        return self.get_env(env_name, *keys, default=default)

    def require_secret(self, env_name, *keys):
        return self.require_env(env_name, *keys)
