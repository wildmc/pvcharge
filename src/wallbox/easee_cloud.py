import requests
from datetime import datetime

from wallbox.base import WallboxBase
from wallbox.models import ChargerState

import logging


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

        #r = requests.post(url, headers=self._headers(), json=payload, timeout=10)
        #r.raise_for_status()
        logging.info("Wallbox: Setting current Limit to %d A for %d min", int(amps), int(duration_min))

    def start_charging(self):
        url = f"{self.base_url}/chargers/{self.charger_id}/start_charging"
        #r = requests.post(url, headers=self._headers(), timeout=10)
        #r.raise_for_status()
        logging.info("Wallbox: Start charging")

    def stop_charging(self):
        url = f"{self.base_url}/chargers/{self.charger_id}/stop_charging"
        #r = requests.post(url, headers=self._headers(), timeout=10)
        #r.raise_for_status()
        logging.info("Wallbox: Stop charging")

    def get_state(self) -> ChargerState:
        url = f"{self.base_url}/chargers/{self.charger_id}/state"
        r = requests.get(url, headers=self._headers(), timeout=10)
        r.raise_for_status()

        data = r.json()

        #logging.info("Wallbox: Raw state: %s", str(data))

        total_power = data.get("totalPower", 0.0)

        charger_state = ChargerState(
            enabled=(total_power > 0.3),
            current_limit=data.get("outputCurrent", 0),
            total_power=total_power * 1000.0,
            timestamp=datetime.now()
        )

        logging.info("Wallbox: State: Enabled: %s CurrentLimit: %.0f TotalPower: %.0f", str(charger_state.enabled), charger_state.current_limit, charger_state.total_power)

        return charger_state
