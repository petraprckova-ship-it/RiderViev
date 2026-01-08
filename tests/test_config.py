"""
Unit testy pro konfiguraci
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from src.config import (
    Config, 
    init_config,
    ProfileManager,
    RobotProfile
)


def test_config_load_default():
    """Test načtení default config"""
    config_path = Path("config/default_config.yaml")
    
    if config_path.exists():
        config = init_config(str(config_path))
        
        assert config is not None
        assert config.app.name == "Person Tracker"
        assert config.app.language == "cs"
        

def test_config_validation():
    """Test validace config hodnot"""
    config = Config()
    
    # Zkontroluj rozsahy
    assert 0 <= config.control.pid['linear'].kp <= 10
    assert 0 <= config.control.pid['angular'].kp <= 10
    
    # Zkontroluj control
    assert config.control.frequency > 0
    assert config.control.watchdog_timeout > 0
    

def test_config_merge():
    """Test slučování config"""
    # Vytvoř dočasný user config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        user_config = {
            'app': {
                'theme': 'light'
            },
            'control': {
                'speed_profile': 'fast'
            }
        }
        yaml.dump(user_config, f)
        user_path = f.name
        
    try:
        # Načti a slučuj
        config = Config()
        merged = config.merge_with_user_config(Path(user_path))
        
        # Zkontroluj
        assert merged.app.theme == 'light'
        assert merged.control.default_profile == 'normal'  # user config neměnil profil
        
    finally:
        Path(user_path).unlink()


def test_profile_manager():
    """Test profile manageru"""
    # Vytvoř dočasný soubor
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        profiles_path = Path(f.name)
        
    try:
        manager = ProfileManager(profiles_path)
        
        # Přidej profil
        profile = RobotProfile(
            name="TestRobot",
            ip="192.168.1.100",
            port=22,
            description="Test"
        )
        
        manager.add_profile(profile)
        
        # Načti profil
        loaded = manager.get_profile("TestRobot")
        assert loaded is not None
        assert loaded.ip == "192.168.1.100"
        
        # Smaž profil
        manager.delete_profile("TestRobot")
        assert manager.get_profile("TestRobot") is None
        
    finally:
        if profiles_path.exists():
            profiles_path.unlink()


def test_config_yaml_structure():
    """Test struktury YAML config souboru"""
    config_path = Path("config/default_config.yaml")
    
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
            
        # Zkontroluj sekce
        assert 'app' in data
        assert 'video' in data
        assert 'ml' in data
        assert 'control' in data
        assert 'safety' in data
        assert 'network' in data
        assert 'ui' in data
