import time
import logging


class PVController:

    def __init__(self, inverter, wallbox, config, mqtt=None):
        self.inverter = inverter
        self.wallbox = wallbox
        self.config = config
        self.mqtt = mqtt

        self.buffer = []
        self.last_wallbox_update = 0
        self.last_wallbox_state_update = time.time()

        self.last_amps = 0

    # -------------------------
    # helpers
    # -------------------------

    def _avg(self):
        if not self.buffer:
            return 0.0
        return sum(self.buffer) / len(self.buffer)

    def _calc_amps(self, surplus_w):
        voltage = self.config["control"]["voltage"]
        amps = int(surplus_w / voltage)

        return max(
            0,
            min(amps, self.config["control"]["max_current"])
        )

    def _should_charge(self, avg_surplus):
        return avg_surplus >= self.config["control"]["surplus_start_threshold"]

    def _should_stop(self, avg_surplus):
        return avg_surplus <= self.config["control"]["surplus_stop_threshold"]

    # -------------------------
    # main loop
    # -------------------------

    def run(self):

        poll_interval = self.config["control"]["poll_interval"]
        update_interval = self.config["control"]["wallbox_update_interval"]
        min_current = self.config["control"]["min_current"]

        wallbox_state = self.wallbox.get_state()
        self.last_wallbox_state_update = time.time()
        self.last_wallbox_update = time.time()

        while True:

            # 1. read inverter
            data = self.inverter.read_power_data()

            self.buffer.append(data.surplus_power)
            if len(self.buffer) > self.config["control"]["averaging_window"]:
                self.buffer.pop(0)

            avg = self._avg() + wallbox_state.total_power
            calculated_amps = self._calc_amps(avg)

            logging.info(
                "Controller: PV=%.0fW House=%.0fW Wallbox=%.0fW Surplus=%.0fW FloatingMean=%.0fW WallBoxEnabled=%d WouldSetMaxCurrent=%dA",
                data.pv_power,
                data.house_power,
                wallbox_state.total_power,
                data.surplus_power,
                avg,
                int(wallbox_state.enabled),
                calculated_amps
            )

            if self.mqtt:
                self.mqtt.publish(data, avg)

            now = time.time()

            # -------------------------
            # 2. state machine
            # -------------------------

            if now - self.last_wallbox_state_update > (update_interval / 2):
                wallbox_state = self.wallbox.get_state()
                self.last_wallbox_state_update = now

                if wallbox_state.enabled and self._should_stop(avg):
                    logging.info("Pause charging (low surplus)")
                    self.wallbox.stop_charging()
                    self.last_amps = 0
                elif self._should_charge(avg) and not wallbox_state.enabled:
                    logging.info("Resume charging")
                    self.wallbox.start_charging()


            # -------------------------
            # 3. wallbox heartbeat (EVERY 4 min)
            # -------------------------

            if now - self.last_wallbox_update > update_interval:

                if wallbox_state.enabled:
                    self.last_wallbox_update = now
                    avg = self._avg() + wallbox_state.total_power
                    amps = self._calc_amps(avg)

                    if amps < min_current:
                        logging.info("Below min current -> would stop charging")
                        self.wallbox.stop_charging()
                        self.last_amps = 0

                    else:
                        # nur aktualisieren wenn Änderung sinnvoll
                        if abs(amps - self.last_amps) >= 1:

                            logging.info(
                                "Will update Easee max current: %dA (TTL refresh)",
                                amps
                            )

                            # ✅ WICHTIG: TTL = fail-safe
                            self.wallbox.set_current_limit(
                                 amps=amps,
                                 duration_min=10
                            )

                            # self.wallbox.start_charging()
                            self.last_amps = amps

                        else:
                            # heartbeat refresh ohne Änderung
                            logging.debug("Refresh TTL only (no amp change)")
                            self.wallbox.set_current_limit(
                                 amps=self.last_amps,
                                 duration_min=10
                            )


            # -------------------------
            # 4. sleep
            # -------------------------

            time.sleep(poll_interval)
