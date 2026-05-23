import requests
from datetime import datetime

from wallbox.base import WallboxBase
from models.models import ChargerState


class EaseeCloudClient(WallboxBase):

    def __init__(self, api_key: str, charger_id: str):
        self.api_key = api_key
        self.charger_id = charger_id
        self.base_url = "https://api.easee.com/api"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    # ✅ WICHTIG: TTL-basierte Steuerung (fail-safe)
    def set_current_limit(self, amps: int, duration_min: int = 10):
        """
        Setzt dynamisches Stromlimit mit Ablaufzeit.
        Wenn der Service abstürzt, fällt die Limitierung nach Ablauf zurück.
        """
        url = (
            f"{self.base_url}/chargers/"
            f"{self.charger_id}/commands/set_dynamic_charger_current"
        )

        payload = {
            "amps": int(amps),
            "minutes": int(duration_min)
        }

        r = requests.post(url, headers=self._headers(), json=payload, timeout=10)
        r.raise_for_status()

    def start_charging(self):
        url = f"{self.base_url}/chargers/{self.charger_id}/start_charging"
        r = requests.post(url, headers=self._headers(), timeout=10)
        r.raise_for_status()

    def stop_charging(self):
        url = f"{self.base_url}/chargers/{self.charger_id}/stop_charging"
        r = requests.post(url, headers=self._headers(), timeout=10)
        r.raise_for_status()

    def get_state(self) -> ChargerState:
        url = f"{self.base_url}/chargers/{self.charger_id}"
        r = requests.get(url, headers=self._headers(), timeout=10)
        r.raise_for_status()

        data = r.json()

        return ChargerState(
            enabled=data.get("isEnabled", False),
            current_limit=data.get("dynamicChargerCurrent", 0),
            timestamp=datetime.now()
        )