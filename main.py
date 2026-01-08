#!/usr/bin/env python3
"""
Person Tracker - Hlavní vstupní bod aplikace
"""

import sys
import asyncio
from pathlib import Path
from loguru import logger
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Import konfigurace
from src.config import init_config, get_config

# Import hlavního okna
from src.ui.main_window import MainWindow


def setup_logging(log_level: str = "INFO"):
    """Nastavení logování"""
    logger.remove()  # Odstraň výchozí handler

    # Console logger s barvami
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )

    # File logger
    log_dir = Path.home() / ".person_tracker" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "person_tracker_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # Nový soubor každý den
        retention="7 days",  # Uchování 7 dní
        compression="zip"
    )

    logger.info("Logging inicializován")


def main():
    """Hlavní funkce"""
    # Nastavení high DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    # Vytvoření Qt aplikace
    app = QApplication(sys.argv)
    app.setApplicationName("Person Tracker")
    app.setOrganizationName("PetraPrckova")
    app.setOrganizationDomain("ship-it.com")

    # Načtení konfigurace
    config_dir = Path.home() / ".person_tracker" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    default_config_path = Path(__file__).parent / "config" / "default_config.yaml"
    user_config_path = config_dir / "user_config.yaml"

    try:
        config = init_config(default_config_path, user_config_path)
    except Exception as e:
        logger.error(f"Chyba při načítání konfigurace: {e}")
        return 1

    # Nastavení logování podle konfigurace
    setup_logging(config.app.log_level)

    logger.info("=" * 80)
    logger.info(f"{config.app.name} v{config.app.version}")
    logger.info("=" * 80)
    logger.info(f"Jazyk: {config.app.language}")
    logger.info(f"Téma: {config.app.theme}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"PyQt6: {QApplication.instance()}")

    # Vytvoření hlavního okna
    try:
        main_window = MainWindow(config)
        main_window.show()

        logger.success("Aplikace spuštěna")

        # Spuštění event loop
        exit_code = app.exec()

        logger.info("Aplikace ukončena")
        return exit_code

    except Exception as e:
        logger.exception(f"Kritická chyba při spuštění: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
