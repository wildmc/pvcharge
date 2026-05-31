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
            "totalPower": 1.2,
            "outputCurrent": 8,
        })
        client = EaseeCloudClient(user_name="user@example.com", charger_id="EH123")

        with (
            patch("wallbox.easee_cloud.getpass", return_value="secret"),
            patch("wallbox.easee_cloud.requests.post", api.post),
            patch("wallbox.easee_cloud.requests.get", api.get),
        ):
            state = client.get_state()

        self.assertTrue(state.enabled)
        self.assertEqual(state.current_limit, 8)
        self.assertEqual(len(api.calls), 2)
        self.assertEqual(api.calls[0]["method"], "POST")
        self.assertEqual(api.calls[0]["url"], "https://api.easee.com/api/accounts/login")
        self.assertEqual(api.calls[0]["json"], {
            "userName": "user@example.com",
            "password": "secret",
        })
        self.assertEqual(api.calls[1]["method"], "GET")
        self.assertEqual(api.calls[1]["url"], "https://api.easee.com/api/chargers/EH123/state")
        self.assertEqual(api.calls[1]["timeout"], 10)
        self.assertEqual(api.calls[1]["headers"]["Authorization"], "Bearer access-token")

    def test_set_current_limit_uses_ttl_payload(self):
        api = MockEaseeApi()
        client = EaseeCloudClient(user_name="user@example.com", charger_id="EH123")

        with (
            patch("wallbox.easee_cloud.getpass", return_value="secret"),
            patch("wallbox.easee_cloud.requests.post", api.post),
        ):
            client.set_current_limit(amps=8, duration_min=10)

        self.assertEqual(len(api.calls), 2)
        self.assertEqual(api.calls[1]["method"], "POST")
        self.assertEqual(
            api.calls[1]["url"],
            "https://api.easee.com/api/chargers/EH123/commands/set_dynamic_charger_current",
        )
        self.assertEqual(api.calls[1]["json"], {"amps": 8, "minutes": 10})
        self.assertEqual(api.calls[1]["timeout"], 10)
        self.assertEqual(api.calls[1]["headers"]["Authorization"], "Bearer access-token")

    def test_start_and_stop_charging_use_easee_api(self):
        api = MockEaseeApi()
        client = EaseeCloudClient(user_name="user@example.com", charger_id="EH123")

        with (
            patch("wallbox.easee_cloud.getpass", return_value="secret"),
            patch("wallbox.easee_cloud.requests.post", api.post),
        ):
            client.start_charging()
            client.stop_charging()

        self.assertEqual(len(api.calls), 3)
        self.assertEqual(
            api.calls[1]["url"],
            "https://api.easee.com/api/chargers/EH123/commands/resume_charging",
        )
        self.assertEqual(
            api.calls[2]["url"],
            "https://api.easee.com/api/chargers/EH123/commands/pause_charging",
        )


if __name__ == "__main__":
    unittest.main()
