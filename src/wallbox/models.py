from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChargerState:
    enabled: bool
    current_limit: int     # A
    total_power: float# W
    timestamp: datetime
