from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChargerState:
    enabled: bool
    current_limit: int
    timestamp: datetime
