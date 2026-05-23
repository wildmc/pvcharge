import json


class MqttClient:

    def __init__(self, client):
        self.client = client

    def publish(self, data, avg):
        payload = {
            "pv": data.pv_power,
            "house": data.house_power,
            "surplus": data.surplus_power,
            "avg": avg
        }

        self.client.publish("pvcharge/status", json.dumps(payload))