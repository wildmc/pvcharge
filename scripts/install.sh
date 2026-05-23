#!/bin/bash

set -e

PROJECT_DIR="/opt/pv-charge-control"

echo "== Installing PV Charge Control =="

# 1. System dependencies
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

# 2. Projektverzeichnis
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# (Optional: falls aus Git)
# git clone https://your-repo.git $PROJECT_DIR

cd $PROJECT_DIR

# 3. Virtualenv
python3 -m venv venv
source venv/bin/activate

# 4. Dependencies
pip install --upgrade pip

cat > requirements.txt << EOF
pymodbus>=3.0
requests>=2.31
PyYAML>=6.0
paho-mqtt>=1.6
EOF

pip install -r requirements.txt

# 5. env placeholder for local secrets
if [ ! -f .env ]; then
cat > .env << EOF
EASEE_API_KEY=
NEOOM_BEAAM_API_TOKEN=
EOF
chmod 600 .env
fi

# 6. config placeholder
if [ ! -f config.yaml ]; then
cat > config.yaml << EOF
inverter:
  host: 192.168.1.50
  port: 502
  unit_id: 1

wallbox:
  mode: cloud
  cloud:
    api_key: ""
    charger_id: ""

control:
  poll_interval: 20
  wallbox_update_interval: 240
  averaging_window: 12
  voltage: 230
  min_current: 6
  max_current: 16

mqtt:
  enabled: false
EOF
fi

echo "== Installing systemd service =="

sudo tee /etc/systemd/system/pv-charge-control.service > /dev/null << EOF
[Unit]
Description=PV Charge Control
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python src/main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-$PROJECT_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

# 7. systemd reload + enable
sudo systemctl daemon-reload
sudo systemctl enable pv-charge-control.service

echo "== Installation complete =="
echo "Start with: sudo systemctl start pv-charge-control"
echo "Logs: journalctl -u pv-charge-control -f"
