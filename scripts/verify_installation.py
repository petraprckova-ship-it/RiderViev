#!/usr/bin/env python3
"""
Ověření instalace - kontrola všech závislostí
"""

import sys
import platform
from pathlib import Path


def check_python_version():
    """Kontrola verze Pythonu"""
    print("🐍 Python verze...")
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print(f"   Verze: {version_str}")

    if version.major == 3 and version.minor >= 11:
        print("   ✓ OK")
        return True
    else:
        print(f"   ✗ CHYBA: Vyžadována Python 3.11+, nalezena {version_str}")
        return False


def check_package(package_name, import_name=None):
    """Kontrola nainstalovaného balíčku"""
    if import_name is None:
        import_name = package_name

    try:
        module = __import__(import_name)
        version = getattr(module, "__version__", "neznámá")
        print(f"   {package_name}: {version} ✓")
        return True
    except ImportError:
        print(f"   {package_name}: ✗ CHYBÍ")
        return False


def check_packages():
    """Kontrola všech balíčků"""
    print("\n📦 Python balíčky...")

    packages = [
        ("PyQt6", "PyQt6"),
        ("NumPy", "numpy"),
        ("OpenCV", "cv2"),
        ("Ultralytics (YOLO)", "ultralytics"),
        ("PyZMQ", "zmq"),
        ("Loguru", "loguru"),
        ("PyYAML", "yaml"),
        ("Pydantic", "pydantic"),
    ]

    all_ok = True
    for pkg_name, import_name in packages:
        if not check_package(pkg_name, import_name):
            all_ok = False

    return all_ok


def check_gpu():
    """Kontrola GPU"""
    print("\n🎮 GPU detekce...")

    # CUDA (NVIDIA)
    try:
        import torch
        if torch.cuda.is_available():
            print(f"   NVIDIA CUDA: ✓")
            print(f"   GPU Count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
            return True
        else:
            print("   NVIDIA CUDA: ✗ Nedostupná")
    except ImportError:
        print("   PyTorch: ✗ Nenainstalován")

    # ROCm (AMD)
    try:
        import torch
        if hasattr(torch, 'hip') and torch.hip.is_available():
            print(f"   AMD ROCm: ✓")
            return True
    except:
        pass

    print("   ⚠️  Žádné GPU nebylo detekováno")
    print("   Aplikace poběží na CPU (pomalejší)")
    return False


def check_models():
    """Kontrola ML modelů"""
    print("\n🤖 ML modely...")

    models_dir = Path(__file__).parent.parent / "models"

    if not models_dir.exists():
        print(f"   ✗ Adresář models/ neexistuje")
        print(f"   Spusťte: python scripts/download_models.py")
        return False

    required_models = [
        "yolo11s.pt",
        "yolo11n.pt"
    ]

    all_ok = True
    for model in required_models:
        model_path = models_dir / model
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"   {model}: {size_mb:.1f} MB ✓")
        else:
            print(f"   {model}: ✗ CHYBÍ")
            all_ok = False

    if not all_ok:
        print(f"\n   Stáhněte modely: python scripts/download_models.py")

    return all_ok


def check_config():
    """Kontrola konfigurace"""
    print("\n⚙️  Konfigurace...")

    config_path = Path(__file__).parent.parent / "config" / "default_config.yaml"

    if config_path.exists():
        print(f"   default_config.yaml: ✓")
        return True
    else:
        print(f"   default_config.yaml: ✗ CHYBÍ")
        return False


def check_system():
    """Informace o systému"""
    print("\n💻 Systém...")
    print(f"   OS: {platform.system()} {platform.release()}")
    print(f"   Architektura: {platform.machine()}")
    print(f"   Python implementace: {platform.python_implementation()}")


def main():
    """Hlavní funkce"""
    print("=" * 60)
    print("Person Tracker - Ověření instalace")
    print("=" * 60)

    results = []

    results.append(("Python verze", check_python_version()))
    results.append(("Python balíčky", check_packages()))
    results.append(("GPU", check_gpu()))
    results.append(("ML modely", check_models()))
    results.append(("Konfigurace", check_config()))

    check_system()

    # Souhrn
    print("\n" + "=" * 60)
    print("📊 SOUHRN")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ OK" if passed else "✗ CHYBA"
        print(f"{name.ljust(20)}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✅ Všechny kontroly prošly!")
        print("\nMůžete spustit aplikaci:")
        print("  python main.py")
        return 0
    else:
        print("\n⚠️  Některé kontroly selhaly!")
        print("\nOpravte chyby a spusťte znovu:")
        print("  python scripts/verify_installation.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
