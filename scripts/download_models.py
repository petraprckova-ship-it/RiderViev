#!/usr/bin/env python3
"""
Skript pro stažení ML modelů
"""

import sys
from pathlib import Path
from urllib.request import urlretrieve
from loguru import logger
import hashlib


def download_with_progress(url: str, dest: Path):
    """Stáhni soubor s progress barem"""
    logger.info(f"Stahuji {dest.name}...")

    def progress_hook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        sys.stdout.write(f"\r  Průběh: [{('=' * (percent // 2)).ljust(50)}] {percent}%")
        sys.stdout.flush()

    urlretrieve(url, dest, progress_hook)
    sys.stdout.write("\n")
    logger.success(f"✓ Staženo: {dest.name}")


def verify_checksum(file_path: Path, expected_md5: str) -> bool:
    """Ověř MD5 checksum"""
    logger.info(f"Ověřuji {file_path.name}...")
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)

    actual_md5 = md5_hash.hexdigest()
    if actual_md5 == expected_md5:
        logger.success(f"✓ Checksum OK")
        return True
    else:
        logger.error(f"✗ Checksum nesouhlasí! Očekáváno: {expected_md5}, Aktuální: {actual_md5}")
        return False


def main():
    """Hlavní funkce"""
    logger.info("=" * 60)
    logger.info("Person Tracker - Stahování ML modelů")
    logger.info("=" * 60)

    # Vytvoř models adresář
    models_dir = Path(__file__).parent.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Seznam modelů ke stažení
    models = [
        {
            "name": "YOLO11-nano",
            "filename": "yolo11n.pt",
            "url": "https://github.com/ultralytics/assets/releases/download/v8.1.0/yolo11n.pt",
            "md5": None,  # Aktualizujte s skutečným MD5
        },
        {
            "name": "YOLO11-small",
            "filename": "yolo11s.pt",
            "url": "https://github.com/ultralytics/assets/releases/download/v8.1.0/yolo11s.pt",
            "md5": None,
        },
    ]

    logger.info(f"Cílový adresář: {models_dir}")
    logger.info("")

    # Stáhni modely
    for model in models:
        dest = models_dir / model["filename"]

        if dest.exists():
            logger.info(f"⊙ Model již existuje: {model['name']}")
            if model["md5"]:
                verify_checksum(dest, model["md5"])
            continue

        try:
            download_with_progress(model["url"], dest)

            if model["md5"]:
                if not verify_checksum(dest, model["md5"]):
                    logger.warning("Checksum nesouhlasí, model může být poškozen")

        except Exception as e:
            logger.error(f"✗ Chyba při stahování {model['name']}: {e}")
            if dest.exists():
                dest.unlink()
            continue

    logger.info("")
    logger.info("=" * 60)
    logger.success("✓ Stahování dokončeno!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Stažené modely:")
    for file in models_dir.glob("*.pt"):
        size_mb = file.stat().st_size / (1024 * 1024)
        logger.info(f"  • {file.name} ({size_mb:.1f} MB)")

    logger.info("")
    logger.info("Můžete nyní spustit aplikaci:")
    logger.info("  python main.py")


if __name__ == "__main__":
    main()
