import requests
from datetime import datetime

from wallbox.base import WallboxBase
from models.models import ChargerState


class EaseeLocalClient(WallboxBase):

    def __init__(self, host: str):
        self.base_url = f"http://{host}"

    def set_current_limit(self, amps: int):
        requests.post(f"{self.base_url}/set_current", json={"amps": amps})

    def start_charging(self):
        requests.post(f"{self.base_url}/start")

    def stop_charging(self):
        requests.post(f"{self.base_url}/stop")

    def get_state(self) -> ChargerState:
        r = requests.get(f"{self.base_url}/status").json()

        return ChargerState(
            enabled=r["enabled"],
            current_limit=r["current"],
            timestamp=datetime.now()
        )