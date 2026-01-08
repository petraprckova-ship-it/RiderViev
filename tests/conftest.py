"""
Test konfigurace
"""

import pytest


def test_import():
    """Test importu všech modulů"""
    import src.config
    import src.ml.detector
    import src.ml.tracker
    import src.ml.distance
    import src.network.client
    import src.control.pid
    import src.control.tracking
    
    assert True


@pytest.fixture
def sample_config():
    """Fixture pro testovací config"""
    from src.config import Config
    return Config()
