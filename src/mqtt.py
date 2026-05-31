import json
import logging

import paho.mqtt.client as mqtt


class MqttClient:

    def __init__(self, client, topic_prefix="pvcharge", qos=0, retain=False):
        self.client = client
        self.topic_prefix = topic_prefix.strip("/")
        self.qos = qos
        self.retain = retain

    @classmethod
    def from_config(cls, config):
        host = config.get("host", "127.0.0.1")
        port = int(config.get("port", 1883))
        keepalive = int(config.get("keepalive", 60))
        client_id = config.get("client_id", "pv-charge-control")

        client = mqtt.Client(client_id=client_id)
        client.connect(host, port, keepalive)
        client.loop_start()

        return cls(
            client=client,
            topic_prefix=config.get("topic_prefix", "pvcharge"),
            qos=int(config.get("qos", 0)),
            retain=bool(config.get("retain", False)),
        )

    def publish(self, data, avg):
        payload = {
            "pv": data.pv_power,
            "house": data.house_power,
            "surplus": data.surplus_power,
            "avg": avg
        }

        try:
            self.client.publish(
                f"{self.topic_prefix}/status",
                json.dumps(payload),
                qos=self.qos,
                retain=self.retain,
            )
        except Exception as exc:
            logging.warning("MQTT publish failed: %s", exc)

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()
