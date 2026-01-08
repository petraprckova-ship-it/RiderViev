# Rychlý start průvodce

## 🚀 Spuštění za 5 minut

### Krok 1: Stažení a instalace (Desktop)

```bash
# Klonování
git clone https://github.com/petraprckova-ship-it/RiderViev.git
cd RiderViev

# Virtuální prostředí
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate na Windows

# Instalace
pip install -r requirements.txt

# Stažení modelů
python scripts/download_models.py
```

### Krok 2: Nastavení robota

```bash
# Připojte se k robotu
ssh pi@<robot-ip>

# Rychlá instalace
wget https://raw.githubusercontent.com/petraprckova-ship-it/RiderViev/main/robot/install.sh
chmod +x install.sh
./install.sh

# Restart
sudo reboot
```

### Krok 3: První spuštění

```bash
# Na desktop stanici
python main.py
```

### Krok 4: Připojení

1. V aplikaci klikněte na **"Nový profil"**
2. Zadejte IP adresu robota
3. Klikněte **"Připojit"**
4. Vyberte režim **"Auto-sledování"**
5. Robot začne sledovat osobu! 🎉

---

## 🎮 Ovládání

### Klávesové zkratky

| Klávesa | Akce |
|---------|------|
| **Space** | Nouzové zastavení |
| **Ctrl+A** | Režim Auto-sledování |
| **Ctrl+M** | Režim Manuální |
| **Ctrl+S** | Režim Stop |
| **F11** | Celá obrazovka |
| **Ctrl+Q** | Ukončit |

### Manuální ovládání (když je aktivní režim Manual)

| Klávesa | Pohyb |
|---------|-------|
| **W** | Vpřed |
| **S** | Vzad |
| **A** | Vlevo |
| **D** | Vpravo |

---

## ⚙️ Základní nastavení

### Profily rychlosti

**Opatrný** (pro začátečníky):
- Pomalé a plynulé pohyby
- Ideální pro úzké prostory

**Normální** (výchozí):
- Vyvážený výkon
- Pro běžné použití

**Agresivní** (pokročilí):
- Rychlé reakce
- Pro otevřené prostory

### Nastavení vzdálenosti

- **Minimální:** Jak blízko může robot přijet
- **Maximální:** Jak daleko robot sleduje
- **Cílová:** Preferovaná vzdálenost

---

## 🎯 Tipy pro nejlepší výsledky

### Prostředí

✅ **Dobré:**
- Dobře osvětlený prostor
- Rovná podlaha
- Minimální překážky
- WiFi signál > -60 dBm

❌ **Špatné:**
- Tmavé místnosti
- Lesklé povrchy
- Přeplněný prostor
- Slabý WiFi signál

### Sledování osob

✅ **Nejlepší:**
- Osoba v plném osvětlení
- Kontrast oproti pozadí
- Vzdálenost 1-3 metry

❌ **Problematické:**
- Osoba v protisvětle
- Velmi podobné oblečení jako pozadí
- Příliš rychlé pohyby

---

## 🔧 Rychlé řešení problémů

### Robot se nepohybuje

1. Zkontrolujte **baterii** (min. 20%)
2. Ověřte **připojení** (zelený indikátor)
3. Zkuste **režim Stop** → **Auto-sledování**
4. Stiskněte **Space** 2x (zrušení emergency stop)

### Nízké FPS

1. Snižte **rozlišení**: Nastavení → Camera → 320x240
2. Přepněte na **YOLO11-nano**: Nastavení → Detection → Model
3. Zakažte **depth estimation**: Nastavení → Detection → Depth → Off

### Video nefunguje

1. **Restartujte robot service:**
   ```bash
   ssh pi@<robot-ip>
   sudo systemctl restart person-tracker
   ```

2. **Zkontrolujte kameru:**
   ```bash
   libcamera-hello
   ```

### Vysoká latence

1. Použijte **kabelové Ethernet** místo WiFi
2. Snižte **bitrate videa**: Nastavení → Camera → Bitrate
3. Přepněte na **ultra-low latency**: Nastavení → Camera → Latency Mode

---

## 📊 Monitorování výkonu

### V aplikaci

- **FPS counter** (pravý horní roh videa)
- **Latence** (v telemetrii)
- **Battery** (v telemetrii)
- **Network kvalita** (status bar)

### Terminál (pokročilé)

```bash
# GPU využití
nvidia-smi -l 1

# CPU využití
htop

# Síť
iftop -i wlan0
```

---

## 🆘 Nouzové situace

### Robot se chová nepředvídatelně

1. **OKAMŽITĚ** stiskněte **Space** (nouzové zastavení)
2. Odpojte baterii (pokud není reakce)
3. Zkontrolujte logy: `sudo journalctl -u person-tracker -f`

### Ztráta spojení

- Robot se **automaticky zastaví** po 500ms bez příkazů
- Zkuste **reconnect** v aplikaci
- Restartujte **robot service**

---

## 🎓 Další kroky

### Optimalizace

1. [Kalibrace kamery](docs/calibration.md)
2. [Ladění PID](docs/pid_tuning.md)
3. [Custom profily](docs/custom_profiles.md)

### Pokročilé funkce

1. [Depth estimation](docs/depth_setup.md)
2. [Obstacle avoidance](docs/obstacles.md)
3. [Geofencing](docs/geofencing.md)

### Vývoj

1. [API dokumentace](docs/api.md)
2. [Custom ML modely](docs/custom_models.md)
3. [Přispívání](CONTRIBUTING.md)

---

## 📞 Podpora

- **GitHub Issues:** [github.com/petraprckova-ship-it/RiderViev/issues](https://github.com/petraprckova-ship-it/RiderViev/issues)
- **Email:** petraprckova@ship-it.com
- **Dokumentace:** [docs/](docs/)

---

## ⚠️ Bezpečnost

### VŽDY:

- ✅ Používejte v **bezpečném prostoru**
- ✅ Mějte po ruce **nouzové tlačítko**
- ✅ Sledujte robot **vizuálně**
- ✅ Zkontrolujte **okolí** před startem

### NIKDY:

- ❌ Blízko **schodů** nebo **výškových rozdílů**
- ❌ V přítomnosti **malých dětí** nebo **zvířat** bez dohledu
- ❌ Na **mokrých** nebo **skluzných** površích
- ❌ S **nízkou baterií** (<20%)

---

**🎉 Užijte si sledování osob s vaším robotem!**
