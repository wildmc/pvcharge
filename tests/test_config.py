import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Config


class ConfigTest(unittest.TestCase):

    def test_get_returns_nested_values_and_default(self):
        cfg = Config(raw={"control": {"voltage": 230.0}})

        self.assertEqual(cfg.get("control", "voltage"), 230.0)
        self.assertEqual(cfg.get("control", "missing", default=42), 42)
        self.assertEqual(cfg.get("missing", "key", default="fallback"), "fallback")

    def test_require_raises_for_missing_value(self):
        cfg = Config(raw={"control": {}})

        with self.assertRaisesRegex(ValueError, "Missing config key: control.voltage"):
            cfg.require("control", "voltage")

    def test_environment_overrides_runtime_config_values(self):
        cfg = Config(raw={
            "inverter": {
                "neoom_beaam": {"host": "", "token": ""},
                "solax_modbus": {"host": ""},
            },
            "wallbox": {
                "local": {"host": ""},
                "cloud": {"api_key": ""},
            },
        })

        with patch.dict(os.environ, {
            "NEOOM_BEAAM_HOST": "beaam.local",
            "NEOOM_BEAAM_API_TOKEN": "token",
            "SOLAX_MODBUS_HOST": "solax.local",
            "EASEE_LOCAL_HOST": "easee.local",
            "EASEE_USER_NAME": "easee-token",
        }, clear=True):
            cfg.apply_env_overrides()

        self.assertEqual(cfg.get("inverter", "neoom_beaam", "host"), "beaam.local")
        self.assertEqual(cfg.get("inverter", "neoom_beaam", "token"), "token")
        self.assertEqual(cfg.get("inverter", "solax_modbus", "host"), "solax.local")
        self.assertEqual(cfg.get("wallbox", "local", "host"), "easee.local")
        self.assertEqual(cfg.get("wallbox", "cloud", "user_name"), "easee-token")

    def test_require_env_prefers_environment_over_yaml(self):
        cfg = Config(raw={"inverter": {"neoom_beaam": {"host": "yaml-host"}}})

        with patch.dict(os.environ, {"NEOOM_BEAAM_HOST": "env-host"}, clear=True):
            value = cfg.require_env("NEOOM_BEAAM_HOST", "inverter", "neoom_beaam", "host")

        self.assertEqual(value, "env-host")

    def test_load_reads_explicit_yaml_without_project_config(self):
        yaml_content = """
control:
  voltage: 230.0
inverter:
  neoom_beaam:
    host: yaml-host
    token: yaml-token
"""

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"
            config_path.write_text(yaml_content, encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                with patch.object(Config, "resolve_env_path", return_value=None):
                    cfg = Config.load(str(config_path))

        self.assertEqual(cfg.get("control", "voltage"), 230.0)
        self.assertEqual(cfg.get("inverter", "neoom_beaam", "host"), "yaml-host")


if __name__ == "__main__":
    unittest.main()
