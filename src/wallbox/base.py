from abc import ABC, abstractmethod

from wallbox.models import ChargerState


class WallboxBase(ABC):

    @abstractmethod
    def set_current_limit(self, amps: int):
        pass

    @abstractmethod
    def start_charging(self):
        pass

    @abstractmethod
    def stop_charging(self):
        pass

    @abstractmethod
    def get_state(self) -> ChargerState:
        pass
