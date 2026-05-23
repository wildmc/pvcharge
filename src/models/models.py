from dataclasses import dataclass
from datetime import datetime


@dataclass
class PowerData:
    pv_power: float
    house_power: float
    surplus_power: float
    timestamp: datetime


@dataclass
class ChargerState:
    enabled: bool
    current_limit: int
    timestamp: datetime