import time
import logging

from collections import deque


class NaivePVController:

    def __init__(self, inverter, wallbox, config, mqtt=None):
        self.inverter = inverter
        self.wallbox = wallbox
        self.config = config
        self.mqtt = mqtt

        self.buffer = deque(maxlen=config["control"]["averaging_window"])

        self.last_update = 0
        self.last_state = None

    def _moving_avg(self):
        if not self.buffer:
            return 0
        return sum(self.buffer) / len(self.buffer)

    def _calc_amps(self, surplus_w):
        voltage = self.config["control"]["voltage"]
        amps = int(surplus_w / voltage)

        return max(
            0,
            min(amps, self.config["control"]["max_current"])
        )

    def run(self):
        poll_interval = self.config["control"]["poll_interval"]
        update_interval = self.config["control"]["wallbox_update_interval"]

        while True:
            data = self.inverter.read_power_data()
            self.buffer.append(data.surplus_power)

            avg = self._moving_avg()

            logging.info(
                "PV=%.1fW House=%.1fW Surplus=%.1fW Avg=%.1fW",
                data.pv_power,
                data.house_power,
                data.surplus_power,
                avg
            )

            if self.mqtt:
                self.mqtt.publish(data, avg)

            now = time.time()

            if now - self.last_update > update_interval:
                amps = self._calc_amps(avg)

                min_a = self.config["control"]["min_current"]

                if amps < min_a:
                    logging.info("Stopping charging (low surplus)")
                    self.wallbox.stop_charging()
                else:
                    logging.info("Setting wallbox current: %d A", amps)
                    self.wallbox.set_current_limit(amps)
                    self.wallbox.start_charging()

                self.last_update = now

            time.sleep(poll_interval)