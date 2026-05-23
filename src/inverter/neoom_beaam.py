from datetime import datetime
import logging

import requests

from inverter.base import InverterBase
from models.models import PowerData


logger = logging.getLogger(__name__)


class NeoomBeaamClient(InverterBase):

    def __init__(
        self,
        host: str,
        token: str,
        endpoint: str = "/api/v1/site/state",
        timeout: int = 10,
        keys: dict | None = None,
    ):
        self.base_url = f"http://{host}".rstrip("/")
        self.endpoint = endpoint
        self.timeout = timeout
        self.token = token
        self.keys = keys or {}

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _get_state(self) -> dict:
        response = requests.get(
            f"{self.base_url}{self.endpoint}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _energy_flow_value(state: dict, key: str) -> float:
        states = state.get("energyFlow", {}).get("states", [])

        for item in states:
            if item.get("key") == key:
                value = item.get("value")
                if value is None:
                    raise ValueError(f"BEAAM state key has no value: {key}")
                return float(value)

        raise ValueError(f"Missing BEAAM energyFlow state key: {key}")

    @staticmethod
    def _positive(value: float) -> float:
        return value if value > 0 else 0.0

    def read_power_data(self) -> PowerData:
        state = self._get_state()
        return self._power_data_from_state(state)

    def _power_data_from_state(self, state: dict) -> PowerData:
        pv_key = self.keys.get("pv_power", "POWER_PRODUCTION")
        house_key = self.keys.get("house_power", "POWER_CONSUMPTION_CALC")

        pv = self._positive(self._energy_flow_value(state, pv_key))
        house = abs(self._energy_flow_value(state, house_key))
        surplus = pv - house

        return PowerData(
            pv_power=pv,
            house_power=house,
            surplus_power=surplus,
            timestamp=datetime.now(),
        )

    def print_registers(self):
        state = self._get_state()
        data = self._power_data_from_state(state)

        logger.info("BEAAM API: %s%s", self.base_url, self.endpoint)
        logger.info("PV power: %.0f W", data.pv_power)
        logger.info("House power: %.0f W", data.house_power)
        logger.info("Surplus power: %.0f W", data.surplus_power)

        logger.info("Available energyFlow states:")
        for item in state.get("energyFlow", {}).get("states", []):
            logger.info("  %s: %s", item.get("key"), item.get("value"))
