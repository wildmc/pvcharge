import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from api_mocks import MockEaseeApi
from wallbox.easee_cloud import EaseeCloudClient


class EaseeCloudClientTest(unittest.TestCase):

    def test_get_state_uses_easee_api(self):
        api = MockEaseeApi({
            "isEnabled": True,
            "dynamicChargerCurrent": 8,
        })
        client = EaseeCloudClient(api_key="token", charger_id="EH123")

        with patch("wallbox.easee_cloud.requests.get", api.get):
            state = client.get_state()

        self.assertTrue(state.enabled)
        self.assertEqual(state.current_limit, 8)
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(api.calls[0]["method"], "GET")
        self.assertEqual(api.calls[0]["url"], "https://api.easee.com/api/chargers/EH123")
        self.assertEqual(api.calls[0]["timeout"], 10)
        self.assertEqual(api.calls[0]["headers"]["Authorization"], "Bearer token")

    def test_set_current_limit_uses_ttl_payload(self):
        api = MockEaseeApi()
        client = EaseeCloudClient(api_key="token", charger_id="EH123")

        with patch("wallbox.easee_cloud.requests.post", api.post):
            client.set_current_limit(amps=8, duration_min=10)

        self.assertEqual(len(api.calls), 1)
        self.assertEqual(api.calls[0]["method"], "POST")
        self.assertEqual(
            api.calls[0]["url"],
            "https://api.easee.com/api/chargers/EH123/commands/set_dynamic_charger_current",
        )
        self.assertEqual(api.calls[0]["json"], {"amps": 8, "minutes": 10})
        self.assertEqual(api.calls[0]["timeout"], 10)
        self.assertEqual(api.calls[0]["headers"]["Authorization"], "Bearer token")

    def test_start_and_stop_charging_use_easee_api(self):
        api = MockEaseeApi()
        client = EaseeCloudClient(api_key="token", charger_id="EH123")

        with patch("wallbox.easee_cloud.requests.post", api.post):
            client.start_charging()
            client.stop_charging()

        self.assertEqual(len(api.calls), 2)
        self.assertEqual(
            api.calls[0]["url"],
            "https://api.easee.com/api/chargers/EH123/start_charging",
        )
        self.assertEqual(
            api.calls[1]["url"],
            "https://api.easee.com/api/chargers/EH123/stop_charging",
        )


if __name__ == "__main__":
    unittest.main()
