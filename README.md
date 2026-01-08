# 🤖 Person Tracker - Yahboom Rider Pi CM4

Aplikace pro automatické sledování osob pomocí robota Yahboom Rider Pi CM4 s využitím YOLO11 a ByteTrack algoritmů.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-orange.svg)

## ✨ Hlavní funkce

- 🎯 **Automatické sledování osob** - YOLO11 detekce + ByteTrack tracking
- 🎮 **Interaktivní ovládání** - PyQt6 GUI s real-time video streamem
- 🔄 **Distribuovaná architektura** - Desktop aplikace + robot service přes ZeroMQ
- 🛡️ **Bezpečnostní mechanismy** - Watchdog timer, zónové omezení rychlosti, emergency stop
- 📊 **Telemetrie v reálném čase** - Baterie, senzory, grafy rychlosti
- 🎨 **Moderní UI** - Catppuccin tema (světlé/tmavé režimy)
- 🚀 **GPU akcelerace** - TensorRT optimalizace pro NVIDIA GPU

## 📦 Struktura projektu

```
RiderViev/
├── src/                    # Zdrojový kód desktop aplikace
│   ├── ml/                 # ML pipeline (YOLO11, ByteTrack, distance estimation)
│   ├── control/            # Kontrolní systém (PID, tracking controller)
│   ├── network/            # ZeroMQ komunikace
│   ├── ui/                 # PyQt6 uživatelské rozhraní
│   │   └── widgets/        # UI komponenty (control, video, telemetry)
│   ├── video/              # GStreamer video streaming
│   └── config.py           # Konfigurace (Pydantic)
├── robot/                  # Robot-side service (běží na Raspberry Pi)
│   ├── robot_service.py    # ZeroMQ server
│   ├── yahboom_driver.py   # Hardware driver pro Yahboom Rider
│   └── install.sh          # Instalační skript pro RPi
├── config/                 # Konfigurační soubory
├── docs/                   # Dokumentace
├── tests/                  # Unit a integrační testy
├── scripts/                # Pomocné skripty
└── main.py                 # Entry point
```

## 🚀 Rychlý start

### Windows (One-Line Install) ⚡

```powershell
# PowerShell - zkopírujte a vložte celý řádek (stáhne projekt + nainstaluje vše):
git clone https://github.com/petraprckova-ship-it/RiderViev.git; cd RiderViev; python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt; python main.py
```

```cmd
# CMD (Command Prompt) - alternativa:
git clone https://github.com/petraprckova-ship-it/RiderViev.git && cd RiderViev && python -m venv venv && call venv\Scripts\activate.bat && pip install -r requirements.txt && python main.py
```

**NEBO** stáhněte projekt a poklikejte na: **`QUICK_INSTALL.bat`**

📄 Všechny varianty instalace: [INSTALL_ONELINER.txt](INSTALL_ONELINER.txt)  
📖 Detailní návod: [docs/windows_installation.md](docs/windows_installation.md)

---

### Linux/macOS

```bash
# 1. Klonování repozitáře
git clone https://github.com/petraprckova-ship-it/RiderViev.git
cd RiderViev

# 2. Vytvoření virtuálního prostředí
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# nebo: venv\Scripts\activate  # Windows

# 3. Instalace závislostí
pip install -r requirements.txt

# 4. Stažení ML modelů
python scripts/download_models.py

# 5. Spuštění aplikace
python main.py
```

### Instalace na robot (Raspberry Pi)

```bash
# Připojení přes SSH
ssh pi@192.168.1.100

# Stažení instalačního skriptu
wget https://raw.githubusercontent.com/petraprckova-ship-it/RiderViev/main/robot/install.sh

# Spuštění instalace
chmod +x install.sh
sudo ./install.sh
```

Detailní instrukce: [docs/installation.md](docs/installation.md)

## 🎮 Ovládání

### Klávesové zkratky

| Zkratka | Akce |
|---------|------|
| `Space` | Nouzové zastavení |
| `Ctrl+A` | Auto-sledování |
| `Ctrl+M` | Manuální režim |
| `Ctrl+S` | Stop režim |
| `W/A/S/D` | Manuální pohyb |
| `↑/↓` | Změna rychlosti |
| `F11` | Celá obrazovka |
| `Ctrl+Q` | Ukončení |

### Režimy

- **🎯 Auto-sledování** - Automatické sledování vybrané osoby
- **⌨️ Manuální** - Ovládání klávesnicí (WASD)
- **🔄 Hlídkování** - Rotace a hledání osob (TODO)
- **🛑 Stop** - Zastaveno

## 📖 Dokumentace

- [📥 Instalační návod](docs/installation.md) - Kompletní instalace pro desktop + robot
- [⚡ Quick Start](docs/quick_start.md) - 5minutový průvodce pro začátečníky
- [🏗️ Architektura](docs/architecture.md) - Technická dokumentace systému

## 🧪 Testování

```bash
# Spuštění všech testů
pytest tests/ -v

# Testy s coverage
pytest tests/ --cov=src --cov-report=html

# Nebo pomocí Makefile
make test
make test-cov
```

Testovací coverage:
- **Unit testy**: Config, ML pipeline, Control, Hardware
- **Integrační testy**: Full pipeline, Network
- **Cílová coverage**: >80%

## 🔧 Development

```bash
# Instalace dev závislostí
pip install -r requirements-dev.txt

# Code formatting
black src/ tests/
isort src/ tests/

# Linting
flake8 src/
pylint src/
mypy src/

# Nebo pomocí Makefile
make format
make lint
```

## 🐳 Docker

```bash
# Build image
docker-compose build

# Spuštění aplikace
docker-compose up desktop

# Spuštění mock robota
docker-compose up robot-mock
```

## 🤝 Přispívání

1. Fork repozitáře
2. Vytvoř feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit změny (`git commit -m 'Add some AmazingFeature'`)
4. Push do branch (`git push origin feature/AmazingFeature`)
5. Otevři Pull Request

## 📊 CI/CD

GitHub Actions workflows:
- **CI Pipeline** - Testy, linting, coverage
- **Release** - Automatické buildy pro releases
- **Robot Deploy** - Deployment na robot přes SSH

## 🐛 Známé problémy

- Video stream vyžaduje GStreamer s RTSP podporou
- Hardware driver vyžaduje I2C (smbus) na Raspberry Pi
- TensorRT optimalizace pouze pro NVIDIA GPU

## 📝 TODO

- [ ] Implementace hlídkovacího režimu
- [ ] Web UI pro vzdálené ovládání
- [ ] Multi-robot podpora
- [ ] Voice control integration
- [ ] Mobilní aplikace

## 📄 License

Tento projekt je licencován pod MIT licencí - viz [LICENSE](LICENSE) pro detaily.

## 👥 Autoři

- **Petra Prčková** - Initial work

## 🙏 Poděkování

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) - Object detection
- [ByteTrack](https://github.com/ifzhang/ByteTrack) - Multi-object tracking
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [ZeroMQ](https://zeromq.org/) - Networking
- [Catppuccin](https://github.com/catppuccin/catppuccin) - Color scheme

## 📧 Kontakt

Máte otázky? Otevřete issue na GitHubu!

---

Made with ❤️ in Czech Republic
