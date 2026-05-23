from datetime import datetime
import time

from inverter.base import InverterBase
from models.models import PowerData
from pymodbus.client import ModbusTcpClient


class SolaxModbusClient(InverterBase):

    def __init__(self, host: str, port: int, unit_id: int, registers: dict):
        self.host = host
        self.port = port
        self.client = ModbusTcpClient(host, port=port)
        self.unit_id = unit_id
        self.reg = registers

    def _read_u16(self, reg: int) -> float:
        rr = self.client.read_input_registers(reg, count=1, device_id=self.unit_id)
        return rr.registers[0] if rr else 0.0

    def read_power_data(self) -> PowerData:
        self.client.connect()

        pv = float(self._read_u16(self.reg["pv_power"]))
        house = float(self._read_u16(self.reg["house_power"]))

        surplus = pv - house

        return PowerData(
            pv_power=pv,
            house_power=house,
            surplus_power=surplus,
            timestamp=datetime.now()
        )

    def print_registers(self):
        address_candidates = range(1, 104)
        read_methods = [
            ("holding", "read_holding_registers"),
            ("input", "read_input_registers"),
        ]
        counts = [1, 2]
        device_id = 1
        successes = []

        print(f"Testing Modbus TCP {self.host}:{self.port}")
        print("Trying holding/input registers, count=1/count=2, addresses 1..103, device_id=1.")

        for read_name, method_name in read_methods:
            for count in counts:
                for address in address_candidates:
                    print(f"Try {read_name} address={address} count={count} device_id={device_id}")

                    client = ModbusTcpClient(self.host, port=self.port, timeout=3, retries=1)
                    try:
                        if not client.connect():
                            print("  no TCP connection")
                            continue

                        response = getattr(client, method_name)(address, count=count, device_id=device_id)

                        if response is None:
                            print("  no response")
                        elif hasattr(response, "isError") and response.isError():
                            print(f"  Modbus error: {response}")
                        elif hasattr(response, "registers"):
                            registers = response.registers
                            interpreted = self._interpret_registers(registers)
                            successes.append((read_name, address, count, device_id, registers, interpreted))
                            print(
                                f"  SUCCESS: {read_name} address={address} count={count} "
                                f"device_id={device_id} registers={registers} interpreted={interpreted}"
                            )
                            print(
                                "  Plausible config candidate: "
                                f"method={read_name}, unit_id={device_id}, address={address}, count={count}"
                            )
                        else:
                            print(f"  unexpected response: {response}")
                    except Exception as exc:
                        print(f"  failed: {type(exc).__name__}: {exc}")
                    finally:
                        client.close()

                    time.sleep(5)

        if successes:
            print("Successful Modbus combinations:")
            for read_name, address, count, device_id, registers, interpreted in successes:
                print(
                    f"  method={read_name}, address={address}, count={count}, "
                    f"device_id={device_id}, registers={registers}, interpreted={interpreted}"
                )
        else:
            print("No successful Modbus combination found.")

    @staticmethod
    def _interpret_registers(registers: list[int]) -> dict:
        values = {
            "u16": registers[0],
            "i16": registers[0] - 0x10000 if registers[0] & 0x8000 else registers[0],
        }

        if len(registers) >= 2:
            u32_big = (registers[0] << 16) | registers[1]
            u32_little = (registers[1] << 16) | registers[0]
            values.update({
                "u32_big": u32_big,
                "i32_big": u32_big - 0x100000000 if u32_big & 0x80000000 else u32_big,
                "u32_little": u32_little,
                "i32_little": u32_little - 0x100000000 if u32_little & 0x80000000 else u32_little,
            })

        return values
