# 🪟 Instalace a spuštění na Windows

Kompletní návod pro instalaci Person Tracker na Windows 10/11 krok po kroku.

## 📋 Předpoklady

- Windows 10 nebo 11 (64-bit)
- Připojení k internetu
- Administrátorská práva (pro instalaci)

---

## 🔧 Krok 1: Instalace Pythonu

### 1.1 Stažení Pythonu

1. Otevřete webový prohlížeč a jděte na: https://www.python.org/downloads/
2. Stáhněte **Python 3.11** nebo **Python 3.12** (doporučeno 3.11)
   - Klikněte na žluté tlačítko "Download Python 3.11.x"

### 1.2 Instalace Pythonu

1. Spusťte stažený instalátor `python-3.11.x-amd64.exe`
2. **DŮLEŽITÉ:** Zaškrtněte **"Add Python to PATH"** ✅
3. Klikněte na **"Install Now"**
4. Počkejte na dokončení instalace
5. Klikněte na **"Close"**

### 1.3 Ověření instalace

1. Otevřete **Command Prompt** (cmd):
   - Stiskněte `Win + R`
   - Napište `cmd` a stiskněte Enter

2. Zadejte:
```cmd
python --version
```

3. Měli byste vidět: `Python 3.11.x` nebo `Python 3.12.x`

---

## 📦 Krok 2: Stažení projektu

### Možnost A: Git Clone (pokud máte Git)

```cmd
cd %USERPROFILE%\Documents
git clone https://github.com/petraprckova-ship-it/RiderViev.git
cd RiderViev
```

### Možnost B: ZIP download (jednodušší)

1. Jděte na: https://github.com/petraprckova-ship-it/RiderViev
2. Klikněte na zelené tlačítko **"Code"**
3. Klikněte na **"Download ZIP"**
4. Rozbalte ZIP do složky, např. `C:\Users\VasUzivatel\Documents\RiderViev`
5. Otevřete Command Prompt a přejděte do složky:

```cmd
cd %USERPROFILE%\Documents\RiderViev
```

---

## 🔨 Krok 3: Vytvoření virtuálního prostředí

### 3.1 Vytvoření venv

```cmd
python -m venv venv
```

Počkejte, než se vytvoří (může trvat 30-60 sekund).

### 3.2 Aktivace venv

```cmd
venv\Scripts\activate
```

Úspěch poznáte tak, že na začátku příkazové řádky se objeví `(venv)`:
```
(venv) C:\Users\VasUzivatel\Documents\RiderViev>
```

---

## 📚 Krok 4: Instalace závislostí

### 4.1 Upgrade pip

```cmd
python -m pip install --upgrade pip
```

### 4.2 Instalace hlavních závislostí

```cmd
pip install -r requirements.txt
```

⏱️ **Toto může trvat 5-15 minut** v závislosti na rychlosti internetu.
Stahují se velké balíčky jako PyTorch (~2 GB).

### 4.3 Instalace vývojových nástrojů (volitelné)

```cmd
pip install -r requirements-dev.txt
```

---

## 🤖 Krok 5: Stažení ML modelu

Model se stáhne automaticky při prvním spuštění, nebo můžete:

```cmd
python scripts\download_models.py
```

---

## ✅ Krok 6: Ověření instalace

### 6.1 Spuštění smoke testu

```cmd
set PYTHONPATH=%CD%
python scripts\smoke_test.py
```

Měli byste vidět:
```
✅ Smoke test dokončen - základní funkčnost OK!
```

### 6.2 Spuštění testů

```cmd
python -m pytest tests\ -v
```

Měli byste vidět:
```
====== 34 passed in X.XXs ======
```

---

## 🚀 Krok 7: Spuštění aplikace

### 7.1 Spuštění GUI aplikace

```cmd
python main.py
```

### 7.2 Co se stane:

1. Otevře se okno aplikace Person Tracker
2. Uvidíte 3 panely:
   - **Levý**: Ovládání (připojení k robotu, režimy)
   - **Střední**: Video stream (zatím žádný)
   - **Pravý**: Telemetrie (grafy, senzory)

### 7.3 První spuštění:

- Aplikace běží v **offline režimu** bez robota
- Můžete testovat UI a všechny funkce
- Pro připojení k robotu potřebujete:
  - Yahboom Rider robot na stejné síti
  - IP adresu robota (např. `192.168.1.100`)

---

## 🎮 Ovládání aplikace

### Klávesové zkratky:

| Klávesa | Funkce |
|---------|--------|
| `Space` | Nouzové zastavení |
| `Ctrl+A` | Auto-sledování |
| `Ctrl+M` | Manuální režim |
| `W/A/S/D` | Manuální pohyb |
| `↑/↓` | Změna rychlosti |
| `F11` | Celá obrazovka |
| `Ctrl+Q` | Ukončení |

---

## 🔧 Řešení problémů

### Problém: "python" není rozpoznán jako příkaz

**Řešení:**
1. Python nebyl přidán do PATH
2. Přeinstalujte Python a **zaškrtněte "Add Python to PATH"**
3. Nebo použijte `py` místo `python`:
   ```cmd
   py main.py
   ```

### Problém: ModuleNotFoundError při spuštění

**Řešení:**
1. Ujistěte se, že je aktivované venv:
   ```cmd
   venv\Scripts\activate
   ```
2. Přeinstalujte závislosti:
   ```cmd
   pip install -r requirements.txt
   ```

### Problém: Torch instalace selže

**Řešení:**
1. Ručně nainstalujte PyTorch:
   ```cmd
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   ```
2. Poté znovu:
   ```cmd
   pip install -r requirements.txt
   ```

### Problém: Aplikace se nespustí - chyba s Qt

**Řešení:**
1. Nainstalujte Microsoft Visual C++ Redistributable:
   - Stáhněte z: https://aka.ms/vs/17/release/vc_redist.x64.exe
   - Nainstalujte
2. Restartujte počítač
3. Zkuste znovu spustit aplikaci

### Problém: Černé okno video streamu

**To je normální!** Video stream se zobrazí až když:
1. Připojíte se k robotu s kamerou
2. Nebo připojíte USB/IP kameru a nakonfigurujete URL

---

## 📱 Připojení k robotu (volitelné)

Pokud máte Yahboom Rider robot:

1. Připojte robot k stejné Wi-Fi jako PC
2. Zjistěte IP adresu robota (např. `192.168.1.100`)
3. V aplikaci:
   - Zadejte IP adresu do pole **"Robot IP"**
   - Klikněte **"Connect"**
4. Po připojení uvidíte:
   - ✅ Zelený status "Connected"
   - Video stream z kamery robota
   - Aktuální telemetrii (baterie, senzory)

---

## 🆘 Kontakty a podpora

- **GitHub Issues**: https://github.com/petraprckova-ship-it/RiderViev/issues
- **Dokumentace**: `docs/` složka v projektu
- **README**: Hlavní `README.md` pro přehled funkcí

---

## 🎯 Rychlý start checklist

- [ ] Python 3.11/3.12 nainstalován (s PATH)
- [ ] Projekt stažen (git nebo ZIP)
- [ ] Virtuální prostředí vytvořeno (`python -m venv venv`)
- [ ] Venv aktivováno (`venv\Scripts\activate`)
- [ ] Závislosti nainstalovány (`pip install -r requirements.txt`)
- [ ] Smoke test prošel (`python scripts\smoke_test.py`)
- [ ] Aplikace se spustí (`python main.py`)

---

## 🚀 Hotovo!

Nyní máte plně funkční Person Tracker na Windows!

Pro detailní dokumentaci viz:
- `docs/quick_start.md` - Rychlý úvod
- `docs/architecture.md` - Architektura systému
- `README.md` - Hlavní dokumentace
