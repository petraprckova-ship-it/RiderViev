# CHANGELOG

Všechny významné změny v tomto projektu budou dokumentovány v tomto souboru.

Formát je založen na [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
a tento projekt dodržuje [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Přidáno
- ✅ UI widgety (ControlPanel, VideoDisplay, TelemetryPanel)
- ✅ GStreamer video streaming integrace
- ✅ Yahboom Rider hardware driver s I2C komunikací
- ✅ Kompletní sada unit a integračních testů
- ✅ CI/CD pipeline s GitHub Actions
- ✅ Docker podpora (Dockerfile, docker-compose.yml)
- ✅ Makefile pro běžné operace
- ✅ pyproject.toml s nástroji pro code quality

### Změněno
- 🔄 Vylepšený README s kompletními instrukcemi
- 🔄 Rozšířená dokumentace

### Plánováno
- 🔜 Hlídkovací režim
- 🔜 Web UI pro vzdálené ovládání
- 🔜 Multi-robot podpora

## [0.1.0] - 2026-01-07

### Přidáno
- 🎉 První verze projektu
- ✅ Základní ML pipeline (YOLO11, ByteTrack, distance estimation)
- ✅ Control systém (PID, tracking controller)
- ✅ Network komunikace (ZeroMQ client/server)
- ✅ PyQt6 main window
- ✅ Konfigurace systém (Pydantic + YAML)
- ✅ Robot service pro Raspberry Pi
- ✅ Dokumentace (installation, quick_start, architecture)
- ✅ Pomocné skripty (download_models, verify_installation)

[Unreleased]: https://github.com/petraprckova-ship-it/RiderViev/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/petraprckova-ship-it/RiderViev/releases/tag/v0.1.0
