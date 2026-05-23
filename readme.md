Randbedingungen

* Raspberry Pi
* Python 3.11+
* systemd
* SolaX via Modbus TCP
* Easee:
  * bevorzugt lokal
  * fallback Cloud
* kein Webserver
* MQTT optional
* single-threaded
* synchrones Polling
* YAML-Konfiguration
* journald Logging

Die lokale Easee-API ist leider offiziell nicht besonders offen dokumentiert. Deshalb zwei Implementierungen vorsehen:

```text
WallboxBase
├── EaseeLocalClient
└── EaseeCloudClient
```

---

# Vollständige Zielarchitektur

```text
pv-charge-control/
├── main.py
├── config.yaml
├── requirements.txt
├── pvcharge/
│   ├── config.py
│   ├── controller.py
│   ├── mqtt.py
│   ├── models.py
│   ├── util.py
│   │
│   ├── inverter/
│   │   ├── base.py
│   │   └── solax_modbus.py
│   │
│   └── wallbox/
│       ├── base.py
│       ├── easee_local.py
│       └── easee_cloud.py
│
└── systemd/
    └── pv-charge-control.service
```

---

# Datenmodell

## models.py

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PowerData:
    pv_power: float
    house_power: float
    surplus_power: float
    timestamp: datetime


@dataclass
class ChargerState:
    charging_enabled: bool
    current_limit: int
    timestamp: datetime
```

---

# Konfiguration

## config.yaml

```yaml
inverter:
  host: 192.168.1.50
  port: 502
  unit_id: 1

wallbox:
  mode: cloud

  local:
    host: 192.168.1.60

  cloud:
    api_key: YOUR_API_KEY
    charger_id: EHXXXXXXXX

control:
  poll_interval: 20
  wallbox_update_interval: 240

  min_current: 6
  max_current: 16

  voltage: 230

  averaging_window: 12

  surplus_start_threshold: 1500
  surplus_stop_threshold: 1200

mqtt:
  enabled: true
  host: 192.168.1.10
  port: 1883
  topic_prefix: pvcharge
```

---

# Modbus-SolaX-Client

## Ziel

Der Client soll ausschließlich:

* PV-Leistung
* Hausverbrauch

liefern.

Nicht mehr.

Das hält die Schichten sauber.

---

# solax_modbus.py

```python
class SolaxModbusClient(InverterBase):

    def read_power_data(self) -> PowerData:
        ...
```

Intern:

```text
Modbus TCP
→ Register lesen
→ Werte normieren
→ PowerData zurückgeben
```

---

# Welche Register?

Typischerweise:

| Wert       | Register |
| ---------- | -------- |
| PV Power   | 0x0006   |
| Load Power | 0x000A   |

Je nach Firmware abweichend daher konfigurierbar:

```yaml
registers:
  pv_power: 6
  house_power: 10
```

---

# Wallbox-Architektur

## Base Interface

```python
class WallboxBase:

    def set_current_limit(self, amps: int):
        raise NotImplementedError

    def start_charging(self):
        raise NotImplementedError

    def stop_charging(self):
        raise NotImplementedError

    def get_state(self) -> ChargerState:
        raise NotImplementedError
```

---

# Easee Local

## easee_local.py

Nur wenn lokale API stabil funktioniert.

Mögliche Wege:

* lokale HTTP-Endpunkte
* OCPP
* Reverse Engineering

Deshalb:

```python
class EaseeLocalClient(WallboxBase):
    ...
```

intern so aufgebaut:

```text
HTTP REST
oder
Websocket/OCPP
```

Aber exakt dieselbe öffentliche API wie Cloud.

---

# Easee Cloud

## easee_cloud.py

Intern:

```text
OAuth/API-Key
→ REST Calls
→ Charger Control
```

Methoden:

```python
set_current_limit(amps)
start_charging()
stop_charging()
```

---

# Regelalgorithmus

Das ist der Kern.

---

# Polling-Zyklus

Alle 20 Sekunden:

```text
1. Inverter lesen
2. Überschuss berechnen
3. Moving Average aktualisieren
4. MQTT publish
```

---

# Mittelwertbildung

Einfach:

```python
deque(maxlen=12)
```

Dann:

```python
avg_surplus = sum(values) / len(values)
```

12 × 20s = 4 Minuten.

---

# Wallbox-Regelung

Alle 4 Minuten:

Berechnung:

I = \frac{P}{U}

Dann:

```python
target_amps = int(avg_surplus / voltage)
```

Beispiel:

| Überschuss | Strom |
| ---------- | ----- |
| 1400 W     | 6 A   |
| 2300 W     | 10 A  |
| 3700 W     | 16 A  |

---

# Regeln

## Unter 6A

```text
→ stop charging
```

---

## Zwischen 6A und max

```text
→ current limit setzen
→ charging starten
```

---

# Hysterese

Sehr wichtig.

Sonst:

```text
START
STOP
START
STOP
```

bei jeder Wolke.

Darum:

```yaml
surplus_start_threshold: 1500
surplus_stop_threshold: 1200
```

---

# Mindesthaltezeit

Zusätzlich:

```yaml
minimum_state_duration: 600
```

10 Minuten.

Damit bleibt die Box stabil.

---

# MQTT

Optional.

Topic-Struktur:

```text
pvcharge/pv_power
pvcharge/house_power
pvcharge/surplus_power
pvcharge/surplus_avg
pvcharge/charger/current_limit
pvcharge/charger/enabled
```

Das reicht für:

* MQTT Explorer
* Home Assistant
* Grafana
* InfluxDB

---

# Logging

Sehr simpel halten.

```python
logging.info(
    "PV=%dW House=%dW Surplus=%dW Avg=%dW Current=%dA",
    ...
)
```

Keine eigenen Logfiles.

Nur stdout.

systemd/journald reicht völlig.

---

# systemd-Service

## pv-charge-control.service

```ini
[Unit]
Description=PV Charge Control
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/pv-charge-control
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

# Anforderungen

## requirements.txt

```text
pymodbus
requests
PyYAML
paho-mqtt
```

Mehr braucht es fast nicht.

---

# main.py Ablauf

```text
load config
create inverter client
create wallbox client
create mqtt client

while True:
    poll inverter
    update average
    publish mqtt

    every 4 min:
        compute target current
        update wallbox

    sleep(20)
```

Extrem robust.

---

# Warum diese Architektur gut funktioniert

Weil sie:

* deterministisch
* debuggbar
* restartbar
* cloudarm
* wartbar
* erweiterbar

ist.

Bewusst:

* keinen Webstack
* keine Datenbank
* kein asyncio
* keine Container-Orchestrierung
