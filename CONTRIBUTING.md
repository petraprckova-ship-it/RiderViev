# Contributing to Person Tracker

Děkujeme za váš zájem přispět do projektu Person Tracker! 🎉

## Jak přispět

### Reporting Bugs

Pokud najdete chybu:

1. Zkontrolujte, zda již neexistuje [issue](https://github.com/petraprckova-ship-it/RiderViev/issues)
2. Pokud ne, vytvořte nový issue s:
   - Popisem problému
   - Kroky k reprodukci
   - Očekávané chování
   - Screenshots (pokud je to relevantní)
   - Informace o systému (OS, Python verze, atd.)

### Navrhování funkcí

Máte nápad na novou funkci?

1. Vytvořte issue s popisem
2. Diskutujte s maintainery
3. Po schválení můžete začít implementovat

### Pull Requests

1. **Fork** repozitář
2. **Vytvořte branch** pro vaši feature (`git checkout -b feature/amazing-feature`)
3. **Implementujte** změny
4. **Napište testy** pro nový kód
5. **Spusťte testy**: `make test`
6. **Zkontrolujte code quality**: `make lint`
7. **Zformátujte kód**: `make format`
8. **Commitněte** změny (`git commit -m 'Add amazing feature'`)
9. **Pushněte** do branch (`git push origin feature/amazing-feature`)
10. **Otevřete Pull Request**

### Code Style

- Používáme **Black** pro formátování (line length 100)
- **isort** pro import sorting
- **flake8** a **pylint** pro linting
- **mypy** pro type checking

Spusťte před commitem:

```bash
make format
make lint
```

### Commit Messages

Používejte konvenci:

```
feat: Add new feature
fix: Fix bug in tracking
docs: Update installation guide
test: Add tests for PID controller
refactor: Restructure ML pipeline
style: Format code with black
```

### Testing

Všechny nové featury musí mít testy:

```bash
# Spuštění testů
pytest tests/ -v

# S coverage
pytest tests/ --cov=src --cov-report=html
```

Minimální coverage: **80%**

### Dokumentace

- Updatujte README.md pokud měníte API
- Přidejte docstrings ke všem funkcím a třídám
- Updatujte docs/ pokud měníte architekturu

### Development Setup

```bash
# Clone repo
git clone https://github.com/petraprckova-ship-it/RiderViev.git
cd RiderViev

# Create venv
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Download models
python scripts/download_models.py

# Run tests
make test
```

## Code Review Process

1. Všechny PR musí projít CI (testy, linting)
2. Minimálně 1 schválení od maintainer
3. Žádné merge conflicts
4. Všechny konverzace vyřešené

## Community

- Buďte respektující a konstruktivní
- Pomáhejte ostatním
- Sdílejte znalosti

## License

Přispíváním do projektu souhlasíte s MIT licencí.

---

Děkujeme za vaši pomoc! 🙏
