import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from inverter.neoom_beaam import NeoomBeaamClient
from api_mocks import MockNeoomApi


class NeoomBeaamClientTest(unittest.TestCase):

    def test_energy_flow_value_reads_matching_key_as_float(self):
        state = {
            "energyFlow": {
                "states": [
                    {"key": "POWER_PRODUCTION", "value": "1234.5"},
                ]
            }
        }

        value = NeoomBeaamClient._energy_flow_value(state, "POWER_PRODUCTION")

        self.assertEqual(value, 1234.5)

    def test_energy_flow_value_raises_for_missing_key(self):
        state = {"energyFlow": {"states": []}}

        with self.assertRaisesRegex(ValueError, "Missing BEAAM energyFlow state key"):
            NeoomBeaamClient._energy_flow_value(state, "POWER_PRODUCTION")

    def test_power_data_from_state_normalizes_values(self):
        client = NeoomBeaamClient(host="beaam.local", token="token")
        state = {
            "energyFlow": {
                "states": [
                    {"key": "POWER_PRODUCTION", "value": 3200},
                    {"key": "POWER_CONSUMPTION_CALC", "value": -1100},
                ]
            }
        }

        data = client._power_data_from_state(state)

        self.assertEqual(data.pv_power, 3200)
        self.assertEqual(data.house_power, 1100)
        self.assertEqual(data.surplus_power, 2100)

    def test_power_data_from_state_clamps_negative_pv_to_zero(self):
        client = NeoomBeaamClient(host="beaam.local", token="token")
        state = {
            "energyFlow": {
                "states": [
                    {"key": "POWER_PRODUCTION", "value": -50},
                    {"key": "POWER_CONSUMPTION_CALC", "value": 400},
                ]
            }
        }

        data = client._power_data_from_state(state)

        self.assertEqual(data.pv_power, 0)
        self.assertEqual(data.house_power, 400)
        self.assertEqual(data.surplus_power, -400)

    def test_read_power_data_uses_neoom_api(self):
        api = MockNeoomApi({
            "energyFlow": {
                "states": [
                    {"key": "POWER_PRODUCTION", "value": 3200},
                    {"key": "POWER_CONSUMPTION_CALC", "value": 1100},
                ]
            }
        })
        client = NeoomBeaamClient(
            host="beaam.local",
            token="token",
            endpoint="/api/v1/site/state",
            timeout=7,
        )

        with patch("inverter.neoom_beaam.requests.get", api.get):
            data = client.read_power_data()

        self.assertEqual(data.pv_power, 3200)
        self.assertEqual(data.house_power, 1100)
        self.assertEqual(data.surplus_power, 2100)
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(api.calls[0]["url"], "http://beaam.local/api/v1/site/state")
        self.assertEqual(api.calls[0]["timeout"], 7)
        self.assertEqual(api.calls[0]["headers"]["Authorization"], "Bearer token")


if __name__ == "__main__":
    unittest.main()
