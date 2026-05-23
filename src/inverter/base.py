from abc import ABC, abstractmethod

from models.models import PowerData


class InverterBase(ABC):

    @abstractmethod
    def read_power_data(self) -> PowerData:
        pass

    @abstractmethod
    def print_registers(self):
        pass
