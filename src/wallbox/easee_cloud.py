from xml import dom

import requests
from datetime import datetime
from getpass import getpass
from wallbox.base import WallboxBase
from wallbox.models import ChargerState

import logging


class EaseeCloudClient(WallboxBase):

    def __init__(self, user_name: str, charger_id: str):
        self.user_name = user_name
        self.charger_id = charger_id
        self.base_url = "https://api.easee.com/api"
        self._access_token = None
        self._refresh_token = None

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }

    def _post(self, url: str, json, timeout=10):
        if self._access_token is None or self._refresh_token is None:
            self._authenticate()

        r = requests.post(url=url, headers=self._headers(), json=json, timeout=timeout )

        if r.status_code == 401:  # Token abgelaufen -> refresh
            self._refresh_tokens()
            r = requests.post(url=url, headers=self._headers(), json=json, timeout=timeout)

        r.raise_for_status()

        return r.json()

    def _get(self, url: str, timeout=10):
        if self._access_token is None or self._refresh_token is None:
            self._authenticate()

        r = requests.get(url=url, headers=self._headers(), timeout=timeout)
        if r.status_code == 401:  # Token abgelaufen -> refresh
            self._refresh_tokens()
            r = requests.get(url=url, headers=self._headers(), timeout=timeout)

        r.raise_for_status()

        return r.json()

    # ✅ WICHTIG: TTL-basierte Steuerung (fail-safe)
    def set_current_limit(self, amps: int, duration_min: int = 10):
        logging.info("Wallbox: Setting current Limit to %d A for %d min", int(amps), int(duration_min))
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

        self._post(url, payload)

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
        logging.info("Wallbox: Get state: ...")
        url = f"{self.base_url}/chargers/{self.charger_id}/state"
        data = self._get(url)

        logging.info("Wallbox: Raw state: %s", str(data))

        total_power = data.get("totalPower", 0.0)

        charger_state = ChargerState(
            enabled=(total_power > 0.3),
            current_limit=data.get("outputCurrent", 0),
            total_power=total_power * 1000.0,
            timestamp=datetime.now()
        )

        logging.info("Wallbox: State: Enabled: %s CurrentLimit: %.0f TotalPower: %.0f", str(charger_state.enabled), charger_state.current_limit, charger_state.total_power)

        return charger_state

    def _refresh_tokens(self):
        logging.debug("Wallbox: Refresh Tokens: ...")
        url = f"{self.base_url}/accounts/refresh_token"

        r = requests.post(url, headers=self._headers(), timeout=10)
        r.raise_for_status()

        data = r.json()

        self._access_token = data.get("accessToken")
        self._refresh_token = data.get("refreshToken")

    def _authenticate(self):
        logging.debug("Wallbox: Authenticate: ...")
        url = f"{self.base_url}/accounts/login"

        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "userName": self.user_name,
            "password": getpass(f"Password for user {self.user_name}: ")
        }

        r = requests.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()

        tokens = r.json()

        self._access_token = tokens.get("accessToken")
        self._refresh_token = tokens.get("refreshToken")
