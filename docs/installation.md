# Instalační průvodce

## Požadavky

### Desktop stanice

- **OS:** Linux (Ubuntu 20.04+), Windows 10/11, macOS 12+
- **Python:** 3.11 nebo novější
- **GPU:** NVIDIA (GTX 1660+ doporučeno) nebo AMD s ROCm
- **RAM:** Minimálně 8GB, doporučeno 16GB
- **Disk:** Minimálně 5GB volného místa
- **Síť:** WiFi 5 (802.11ac) nebo Gigabit Ethernet

### Robot (Raspberry Pi CM4)

- **Hardware:** Yahboom Rider Pi CM4
- **OS:** Raspberry Pi OS (64-bit, Bullseye nebo novější)
- **Python:** 3.9+
- **RAM:** Minimálně 2GB
- **Síť:** WiFi nebo Ethernet

---

## Instalace na desktop stanici

### 1. Instalace systémových závislostí

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1
```

**Pro NVIDIA GPU:**

```bash
# CUDA Toolkit (pokud není nainstalován)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-3

# TensorRT
# Stáhněte z: https://developer.nvidia.com/tensorrt
# Postupujte podle oficiálního návodu
```

#### Windows

1. Nainstalujte Python 3.11 z [python.org](https://www.python.org/downloads/)
2. Nainstalujte Git z [git-scm.com](https://git-scm.com/)
3. Pro NVIDIA GPU nainstalujte [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)

#### macOS

```bash
brew install python@3.11 git
```

### 2. Klonování repozitáře

```bash
git clone https://github.com/petraprckova-ship-it/RiderViev.git
cd RiderViev
```

### 3. Vytvoření virtuálního prostředí

```bash
python3.11 -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 4. Instalace Python závislostí

```bash
# Základní instalace
pip install --upgrade pip
pip install -r requirements.txt

# Pro NVIDIA GPU (TensorRT)
pip install tensorrt>=8.6.0

# Pro AMD GPU (ROCm)
pip install onnxruntime-directml
```

### 5. Stažení ML modelů

```bash
python scripts/download_models.py
```

Tento skript stáhne:
- YOLO11-small model (~40MB)
- YOLO11-nano model (backup, ~10MB)
- Depth-Anything-V2-Small (~100MB)

Modely se uloží do `models/` adresáře.

### 6. Ověření instalace

```bash
python scripts/verify_installation.py
```

Tento skript zkontroluje:
- Verzi Pythonu
- Nainstalované balíčky
- GPU dostupnost
- CUDA/TensorRT
- Stažené modely

### 7. První spuštění

```bash
python main.py
```

Při prvním spuštění:
1. Vytvoří se konfigurační složka `~/.person_tracker/`
2. Zkopíruje se výchozí konfigurace
3. Otevře se hlavní okno aplikace

---

## Instalace na robot (Raspberry Pi)

### Automatická instalace (doporučeno)

Na Raspberry Pi spusťte:

```bash
# Připojte se k robotu
ssh pi@<robot-ip>

# Stáhněte instalační skript
wget https://raw.githubusercontent.com/petraprckova-ship-it/RiderViev/main/robot/install.sh
chmod +x install.sh

# Spusťte instalaci
./install.sh

# Po dokončení restartujte
sudo reboot
```

### Manuální instalace

```bash
# Aktualizace systému
sudo apt update && sudo apt upgrade -y

# Instalace závislostí
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    i2c-tools \
    python3-smbus \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-{base,good,bad,ugly} \
    gstreamer1.0-rtsp

# Vytvoření adresáře
sudo mkdir -p /opt/person-tracker
sudo chown $USER:$USER /opt/person-tracker
cd /opt/person-tracker

# Virtuální prostředí
python3 -m venv venv
source venv/bin/activate

# Instalace balíčků
pip install pyzmq loguru RPi.GPIO smbus2 numpy

# Stažení robot service
wget https://raw.githubusercontent.com/petraprckova-ship-it/RiderViev/main/robot/robot_service.py
chmod +x robot_service.py

# Vytvoření systemd service
sudo nano /etc/systemd/system/person-tracker.service
# [Zkopírujte obsah z install.sh]

# Aktivace
sudo systemctl daemon-reload
sudo systemctl enable person-tracker.service
sudo systemctl start person-tracker.service
```

### Povolení I2C a kamery

```bash
sudo raspi-config
```

1. Interface Options → I2C → Yes
2. Interface Options → Camera → Yes
3. Finish → Yes (restart)

---

## Nastavení sítě

### Statická IP adresa (doporučeno)

Na Raspberry Pi:

```bash
sudo nano /etc/dhcpcd.conf
```

Přidejte:

```
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1
```

Restartujte:

```bash
sudo systemctl restart dhcpcd
```

### Konfigurace firewallu

Pokud je aktivní firewall, povolte porty:

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 5555/tcp  # Command port
sudo ufw allow 5556/tcp  # Telemetry port
sudo ufw allow 8554/tcp  # RTSP video stream
```

---

## První připojení

### 1. Spusťte desktop aplikaci

```bash
cd RiderViev
source venv/bin/activate  # nebo venv\Scripts\activate na Windows
python main.py
```

### 2. Vytvořte profil robota

V aplikaci:
1. Klikněte na "Nový profil"
2. Zadejte:
   - **Název:** Např. "Můj Robot"
   - **IP adresa:** `192.168.1.100` (nebo vaše IP)
   - **Port:** `22` (SSH)
   - **Username:** `pi`
   - **SSH klíč:** Cesta k vašemu SSH klíči
3. Klikněte "Uložit"

### 3. Připojte se

1. Vyberte profil ze seznamu
2. Klikněte "Připojit"
3. Počkejte na potvrzení připojení (zelený indikátor)

### 4. Otestujte funkce

1. Vyberte režim "Manual"
2. Použijte WASD klávesy pro pohyb
3. Zkontrolujte video stream
4. Ověřte telemetrii v pravém panelu

---

## Troubleshooting

### Desktop aplikace se nespustí

**Chyba: `ModuleNotFoundError`**

```bash
# Ověřte, že jste ve virtuálním prostředí
which python  # Mělo by ukazovat na venv/bin/python

# Reinstalujte závislosti
pip install -r requirements.txt
```

**Chyba: `CUDA not found`**

Pro NVIDIA GPU:
```bash
# Ověřte instalaci CUDA
nvidia-smi
nvcc --version

# Nainstalujte CUDA toolkit
# Viz sekce instalace
```

### Nelze se připojit k robotu

**Zkontrolujte síťové připojení:**

```bash
ping <robot-ip>
```

**Zkontrolujte SSH:**

```bash
ssh pi@<robot-ip>
# Pokud funguje, problém je jinde
```

**Zkontrolujte robot service:**

```bash
ssh pi@<robot-ip>
sudo systemctl status person-tracker.service

# Zobrazit logy
sudo journalctl -u person-tracker -f
```

**Zkontrolujte porty:**

```bash
# Na robotu
netstat -tuln | grep -E '5555|5556|8554'
```

### Nízké FPS

1. **Snižte rozlišení:**
   - Nastavení → Camera → Resolution → 320x240

2. **Přepněte na rychlejší model:**
   - Nastavení → Detection → Model → YOLO11-nano

3. **Zakažte depth estimation:**
   - Nastavení → Detection → Depth → Disabled

4. **Zkontrolujte GPU využití:**
   ```bash
   nvidia-smi -l 1
   # Mělo by být ~90-100% při inferenci
   ```

### Video stream nefunguje

**Zkontrolujte GStreamer:**

```bash
# Na robotu
gst-launch-1.0 --version

# Test kamery
libcamera-hello
```

**Restartujte video service:**

```bash
sudo systemctl restart person-tracker.service
```

---

## Pokročilé nastavení

### Kalibrace kamery

```bash
python scripts/calibrate_camera.py --robot-ip 192.168.1.100
```

Postupujte podle pokynů na obrazovce.

### Ladění PID regulátorů

Viz [docs/pid_tuning.md](pid_tuning.md)

### Custom modely

Nahraďte modely v `models/` vlastními trained modely kompatibilními s YOLO11.

---

## Deinstalace

### Desktop

```bash
# Odstranění virtuálního prostředí
cd RiderViev
rm -rf venv/

# Odstranění konfigurace
rm -rf ~/.person_tracker/

# Odstranění repozitáře
cd ..
rm -rf RiderViev/
```

### Robot

```bash
sudo systemctl stop person-tracker.service
sudo systemctl disable person-tracker.service
sudo rm /etc/systemd/system/person-tracker.service
sudo rm -rf /opt/person-tracker/
```

---

## Podpora

Pro problémy a otázky:
- GitHub Issues: https://github.com/petraprckova-ship-it/RiderViev/issues
- Email: petraprckova@ship-it.com
