#!/bin/bash
# Instalační script pro robot-side service na Raspberry Pi

set -e

echo "=========================================="
echo "Person Tracker Robot Service - Instalace"
echo "=========================================="

# Kontrola, že běží na Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "⚠️  Varování: Toto nemusí být Raspberry Pi"
    read -p "Pokračovat? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Aktualizace systému
echo "📦 Aktualizuji systém..."
sudo apt update
sudo apt upgrade -y

# Instalace závislostí
echo "📦 Instaluji závislosti..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    i2c-tools \
    python3-smbus \
    libopencv-dev \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-{base,good,bad,ugly} \
    gstreamer1.0-rtsp

# Vytvoření virtuálního prostředí
echo "🐍 Vytvářím Python virtuální prostředí..."
cd /opt
sudo mkdir -p person-tracker
sudo chown $USER:$USER person-tracker
cd person-tracker

python3 -m venv venv
source venv/bin/activate

# Instalace Python balíčků
echo "📦 Instaluji Python balíčky..."
pip install --upgrade pip
pip install \
    pyzmq==25.1.2 \
    loguru==0.7.2 \
    RPi.GPIO \
    smbus2 \
    numpy

# Stažení robot service
echo "📥 Stahuji robot service..."
wget -O robot_service.py https://raw.githubusercontent.com/petraprckova-ship-it/RiderViev/main/robot/robot_service.py
chmod +x robot_service.py

# Vytvoření systemd service
echo "⚙️  Vytvářím systemd service..."
sudo tee /etc/systemd/system/person-tracker.service > /dev/null <<EOF
[Unit]
Description=Person Tracker Robot Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/person-tracker
ExecStart=/opt/person-tracker/venv/bin/python /opt/person-tracker/robot_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Povolení I2C
echo "🔧 Povoluji I2C..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
fi

if ! grep -q "^i2c-dev" /etc/modules; then
    echo "i2c-dev" | sudo tee -a /etc/modules
fi

# Aktivace service
echo "✅ Aktivuji service..."
sudo systemctl daemon-reload
sudo systemctl enable person-tracker.service
sudo systemctl start person-tracker.service

# Kontrola stavu
echo ""
echo "=========================================="
echo "✅ Instalace dokončena!"
echo "=========================================="
echo ""
echo "Stav service:"
sudo systemctl status person-tracker.service --no-pager

echo ""
echo "📋 Užitečné příkazy:"
echo "  Restart service:  sudo systemctl restart person-tracker"
echo "  Zastavit service: sudo systemctl stop person-tracker"
echo "  Zobrazit logy:    sudo journalctl -u person-tracker -f"
echo ""
echo "⚠️  Pro kompletní aktivaci I2C proveďte restart:"
echo "  sudo reboot"
