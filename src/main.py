import logging
import time

from config import Config
from controller import PVController

from inverter.neoom_beaam import NeoomBeaamClient


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )


def create_inverter(cfg):
    return NeoomBeaamClient(
        host=cfg.require("inverter", "neoom_beaam", "host"),
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


def main():
    setup_logging()

    cfg = Config.load("config.yaml")

    logging.info("Starting NEOOM BEAAM dry-run controller...")

    inverter = create_inverter(cfg)
    # Easee usage is intentionally disabled for now. The controller only logs
    # the current that would be applied to the wallbox.
    wallbox = None

    controller = PVController(
        inverter=inverter,
        wallbox=wallbox,
        config=cfg.raw,
        mqtt=None,
    )

    try:
        controller.run()
    except KeyboardInterrupt:
        logging.info("Shutdown requested (Ctrl+C)")
    except Exception as e:
        logging.exception("Fatal error: %s", e)
        time.sleep(5)
        raise


if __name__ == "__main__":
    main()
