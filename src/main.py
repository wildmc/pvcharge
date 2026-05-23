import logging
import time

from config import Config
from controller import PVController

from inverter.neoom_beaam import NeoomBeaamClient
from inverter.solax_modbus import SolaxModbusClient
from wallbox.easee_cloud import EaseeCloudClient
from wallbox.easee_local import EaseeLocalClient

from mqtt import MqttClient


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )


def create_inverter(cfg):
    mode = cfg.get("inverter", "mode", default="solax_modbus")

    if mode == "neoom_beaam":
        return NeoomBeaamClient(
            host=cfg.require("inverter", "neoom_beaam", "host"),
            token=cfg.require("inverter", "neoom_beaam", "token"),
            endpoint=cfg.get("inverter", "neoom_beaam", "endpoint", default="/api/v1/site/state"),
            timeout=cfg.get("inverter", "neoom_beaam", "timeout", default=10),
            keys=cfg.get("inverter", "neoom_beaam", "keys", default={}),
        )

    if mode == "solax_modbus":
        return SolaxModbusClient(
            host=cfg.require("inverter", "solax_modbus", "host"),
            port=cfg.get("inverter", "solax_modbus", "port", default=502),
            unit_id=cfg.get("inverter", "solax_modbus", "unit_id", default=1),
            registers=cfg.get("inverter", "solax_modbus", "registers", default={
                "pv_power": 6,
                "house_power": 10
            })
        )

    raise ValueError(f"Unknown inverter mode: {mode}")


def create_wallbox(cfg):

    mode = cfg.get("wallbox", "mode", default="cloud")

    if mode == "local":
        return EaseeLocalClient(
            host=cfg.require("wallbox", "local", "host")
        )

    return EaseeCloudClient(
        api_key=cfg.require("wallbox", "cloud", "api_key"),
        charger_id=cfg.require("wallbox", "cloud", "charger_id")
    )


def create_mqtt(cfg):
    import paho.mqtt.client as mqtt

    if not cfg.get("mqtt", "enabled", default=False):
        return None

    client = mqtt.Client()

    host = cfg.require("mqtt", "host")
    port = cfg.get("mqtt", "port", default=1883)

    client.connect(host, port, 60)

    return MqttClient(client)


def main():
    setup_logging()

    cfg = Config.load("config.yaml")

    logging.info("Starting PV Charge Control...")

    inverter = create_inverter(cfg)
    #wallbox = create_wallbox(cfg)
    #mqtt = create_mqtt(cfg)

    #controller = PVController(
    #    inverter=inverter,
    #    wallbox=wallbox,
    #    config=cfg.raw,
    #    mqtt=mqtt
    #)

    try:
        #controller.run()
        logging.info("Starting inverter diagnostics")
        inverter.print_registers()
    except KeyboardInterrupt:
        logging.info("Shutdown requested (Ctrl+C)")
    except Exception as e:
        logging.exception("Fatal error: %s", e)
        time.sleep(5)
        raise


if __name__ == "__main__":
    main()
