"""
Unit tests for Vortex configuration module.
"""

from vortex.config import get_settings


def test_settings_defaults():
    settings = get_settings()
    assert settings.service_name == "vortex"
    assert settings.service_version == "0.1.0"
    assert settings.is_testing is True


def test_settings_derived_properties():
    settings = get_settings()
    assert "postgresql://" in settings.sync_database_url or "sqlite://" in settings.sync_database_url
