import logging
import time

from config import Config
from controller import PVController
from mqtt import MqttClient

from inverter.neoom_beaam import NeoomBeaamClient
from wallbox.easee_cloud import EaseeCloudClient



def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )


def create_inverter(cfg):
    return NeoomBeaamClient(
        host=cfg.require_env("NEOOM_BEAAM_HOST", "inverter", "neoom_beaam", "host"),
        token=cfg.require_secret(
            "NEOOM_BEAAM_API_TOKEN",
            "inverter",
            "neoom_beaam",
            "token",
        ),
        endpoint=cfg.get("inverter", "neoom_beaam", "endpoint", default="/api/v1/site/state"),
        timeout=cfg.get("inverter", "neoom_beaam", "timeout", default=10),
        keys=cfg.get("inverter", "neoom_beaam", "keys", default={}),
    )


def create_mqtt(cfg):
    mqtt_config = cfg.get("mqtt", default={})
    if not mqtt_config.get("enabled", False):
        return None

    try:
        mqtt_client = MqttClient.from_config(mqtt_config)
        logging.info(
            "MQTT enabled: publishing to %s/status via %s:%s",
            mqtt_config.get("topic_prefix", "pvcharge"),
            mqtt_config.get("host", "127.0.0.1"),
            mqtt_config.get("port", 1883),
        )
        return mqtt_client
    except Exception as exc:
        logging.warning("MQTT disabled: could not connect to broker: %s", exc)
        return None


def main():
    setup_logging()

    cfg = Config.load("config.yaml")

    logging.info("Starting NEOOM BEAAM dry-run controller...")

    inverter = create_inverter(cfg)

    wallbox = EaseeCloudClient(
        user_name=cfg.get("wallbox", "cloud", "user_name"),
        charger_id=cfg.get("wallbox", "cloud", "charger_id")
    )

    mqtt_client = create_mqtt(cfg)

    controller = PVController(
        inverter=inverter,
        wallbox=wallbox,
        config=cfg.raw,
        mqtt=mqtt_client,
    )

    try:
        controller.run()
    except KeyboardInterrupt:
        logging.info("Shutdown requested (Ctrl+C)")
    except Exception as e:
        logging.exception("Fatal error: %s", e)
        time.sleep(5)
        raise
    finally:
        if mqtt_client:
            mqtt_client.close()


if __name__ == "__main__":
    main()
