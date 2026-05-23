import requests
from datetime import datetime

from wallbox.base import WallboxBase
from wallbox.models import ChargerState


class EaseeNaiveCloudClient(WallboxBase):

    def __init__(self, api_key: str, charger_id: str):
        self.api_key = api_key
        self.charger_id = charger_id
        self.base_url = "https://api.easee.com/api"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}"
        }

    def set_current_limit(self, amps: int):
        url = f"{self.base_url}/chargers/{self.charger_id}/settings"
        requests.post(url, headers=self._headers(), json={
            "maxChargerCurrent": amps
        })

    def start_charging(self):
        url = f"{self.base_url}/chargers/{self.charger_id}/start_charging"
        requests.post(url, headers=self._headers())

    def stop_charging(self):
        url = f"{self.base_url}/chargers/{self.charger_id}/stop_charging"
        requests.post(url, headers=self._headers())

    def get_state(self) -> ChargerState:
        url = f"{self.base_url}/chargers/{self.charger_id}"
        r = requests.get(url, headers=self._headers()).json()

        return ChargerState(
            enabled=r.get("isEnabled", False),
            current_limit=r.get("dynamicChargerCurrent", 0),
            timestamp=datetime.now()
        )
